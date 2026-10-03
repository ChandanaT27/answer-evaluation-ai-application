from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Set, Tuple

from spellchecker import SpellChecker

from .embeddings import cosine, get_embedder
from .schemas import (ConceptIn, EvaluateRequest, EvaluateResponse, MistakeOut, QuestionIn,
                      QuestionResult)
from .segmentation import split_answers
from .text_utils import fuzzy_eq, split_sentences, stem, stem_set, tokenize

_spell: Optional[SpellChecker] = None
NEGATIONS = {"not", "no", "never", "cannot", "neither", "nor", "isn't", "doesn't", "don't", "can't", "won't"}


def _speller() -> SpellChecker:
    global _spell
    if _spell is None:
        _spell = SpellChecker()
    return _spell


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _round_half(x: float) -> float:
    return round(x * 2) / 2


def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    emb = get_embedder()
    answers = split_answers(req.text, [q.number for q in req.questions])
    results = [_evaluate_question(q, answers.get(q.number), req.ocr_confidence, emb) for q in req.questions]
    return EvaluateResponse(results=results, embedding_backend=emb.name)


def _concept_keywords(c: ConceptIn) -> List[str]:
    return [c.name] + [k for k in c.keywords if k.strip()]


def _phrase_present(phrase: str, answer_stems: Set[str]) -> bool:
    stems = [stem(t) for t in tokenize(phrase)]
    stems = [s for s in stems if s]
    if not stems:
        return False
    return all(any(fuzzy_eq(s, a) for a in answer_stems) for s in stems)


def _match_concepts(q: QuestionIn, answer: str, emb) -> Tuple[List[ConceptIn], List[ConceptIn]]:
    answer_stems = stem_set(answer)
    sentences = [s for s, _, _ in split_sentences(answer)]
    sent_vecs = emb.encode(sentences) if sentences else []
    matched, missing = [], []
    for c in q.concepts:
        hit = any(_phrase_present(k, answer_stems) for k in _concept_keywords(c))
        if not hit and len(sentences) > 0:
            cv = emb.encode([" ".join(_concept_keywords(c))])[0]
            hit = any(cosine(cv, sv) >= emb.concept_threshold for sv in sent_vecs)
        (matched if hit else missing).append(c)
    return matched, missing


def _vocab(q: QuestionIn) -> Set[str]:
    words = set(tokenize(q.text)) | set(tokenize(q.model_answer))
    for c in q.concepts:
        for k in _concept_keywords(c):
            words |= set(tokenize(k))
    return words


def _detect_mistakes(q: QuestionIn, answer: str, emb) -> List[MistakeOut]:
    out: List[MistakeOut] = []
    spell = _speller()
    vocab = _vocab(q)

    count = 0
    for m in re.finditer(r"\b[A-Za-z]{4,}\b", answer):
        w = m.group()
        lw = w.lower()
        if lw in vocab or w.isupper() or (w[0].isupper() and m.start() > 0):
            continue
        if lw in spell.unknown([lw]):
            fix = spell.correction(lw)
            if fix and fix != lw:
                out.append(MistakeOut(type="SPELLING", description=f"Possible spelling error: '{w}'",
                                      snippet=w, start_offset=m.start(), end_offset=m.end(), suggestion=fix))
                count += 1
                if count >= 15:
                    break

    for m in re.finditer(r"\b(\w+)\s+\1\b", answer, re.IGNORECASE):
        out.append(MistakeOut(type="GRAMMAR", description=f"Repeated word: '{m.group(1)}'", snippet=m.group(),
                              start_offset=m.start(), end_offset=m.end(), suggestion=m.group(1)))
    for m in re.finditer(r"\ba\s+([aeio]\w*)", answer, re.IGNORECASE):
        if m.group(1).lower() not in {"one", "once", "eon"}:
            out.append(MistakeOut(type="GRAMMAR", description="Use 'an' before a vowel sound", snippet=m.group(),
                                  start_offset=m.start(), end_offset=m.end(), suggestion="an " + m.group(1)))
    for m in re.finditer(r"(?<=[.!?]\s)([a-z]\w*)", answer):
        out.append(MistakeOut(type="GRAMMAR", description="Sentence should start with a capital letter",
                              snippet=m.group(1), start_offset=m.start(), end_offset=m.end(),
                              suggestion=m.group(1).capitalize()))
    for m in re.finditer(r"\bi\b(?!\.)", answer):
        out.append(MistakeOut(type="GRAMMAR", description="Pronoun 'I' should be capitalised", snippet="i",
                              start_offset=m.start(), end_offset=m.end(), suggestion="I"))

    out.extend(_content_mistakes(q, answer, emb))
    out.sort(key=lambda x: (x.start_offset is None, x.start_offset or 0))
    return out


def _content_mistakes(q: QuestionIn, answer: str, emb) -> List[MistakeOut]:
    if not q.model_answer.strip():
        return []
    ans_sents = split_sentences(answer)
    model_sents = [s for s, _, _ in split_sentences(q.model_answer)]
    if not ans_sents or not model_sents:
        return []
    a_vecs = emb.encode([s for s, _, _ in ans_sents])
    m_vecs = emb.encode(model_sents)
    out = []
    for (sent, start, end), av in zip(ans_sents, a_vecs):
        sims = [cosine(av, mv) for mv in m_vecs]
        best_i = max(range(len(sims)), key=lambda i: sims[i])
        best = sims[best_i]
        words = tokenize(sent)
        neg_a = bool(NEGATIONS & set(words))
        neg_m = bool(NEGATIONS & set(tokenize(model_sents[best_i])))
        s0 = answer.find(sent, start)
        s0 = start if s0 < 0 else s0
        if neg_a != neg_m and best >= (emb.lo + emb.hi) / 2:
            out.append(MistakeOut(type="INCORRECT_CONTENT",
                                  description="Statement may contradict the model answer (negation differs)",
                                  snippet=sent, start_offset=s0, end_offset=s0 + len(sent)))
        elif len(ans_sents) >= 3 and len(words) >= 5 and best < emb.lo * 0.6:
            out.append(MistakeOut(type="INCORRECT_CONTENT",
                                  description="Sentence appears unrelated to the expected answer",
                                  snippet=sent, start_offset=s0, end_offset=s0 + len(sent)))
    return out


def _feedback(q: QuestionIn, found: bool, marks: float, matched, missing, mistakes, sim_score) -> str:
    if not found:
        return "No answer was detected for this question. Make sure the answer is labelled with its question number."
    ratio = marks / q.max_marks
    parts = []
    if ratio >= 0.85:
        parts.append("Excellent answer that covers the key ideas.")
    elif ratio >= 0.6:
        parts.append("Good answer, but some important points are incomplete.")
    elif ratio >= 0.3:
        parts.append("Partially correct; several key points are missing.")
    else:
        parts.append("The answer shows limited understanding of what was asked.")
    if matched:
        parts.append("Covered: " + ", ".join(c.name for c in matched) + ".")
    if missing:
        parts.append("Revise and include: " + ", ".join(c.name for c in missing) + ".")
    lang = [m for m in mistakes if m.type in ("SPELLING", "GRAMMAR")]
    if lang:
        parts.append(f"Work on spelling/grammar ({len(lang)} issue{'s' if len(lang) != 1 else ''} found).")
    if any(m.type == "INCORRECT_CONTENT" for m in mistakes):
        parts.append("Some statements look incorrect or irrelevant; review the highlighted parts.")
    return " ".join(parts)


def _evaluate_question(q: QuestionIn, answer: Optional[str], ocr_conf: float, emb) -> QuestionResult:
    answer = (answer or "").strip()
    found = len(answer) > 0
    if not found:
        missing = [c.name for c in q.concepts]
        mist = [MistakeOut(type="MISSING_CONCEPT", description=f"Missing concept: {n}") for n in missing]
        return QuestionResult(question_id=q.id, question_number=q.number, answer_text="", answer_found=False,
                              max_marks=q.max_marks, suggested_marks=0.0, similarity=0.0, concept_coverage=0.0,
                              matched_concepts=[], missing_concepts=missing, mistakes=mist,
                              feedback=_feedback(q, False, 0, [], [], [], 0), confidence=0.3)

    sim = 0.0
    if q.model_answer.strip():
        sim = cosine(emb.encode([answer])[0], emb.encode([q.model_answer])[0])
    sim_score = _clamp((sim - emb.lo) / (emb.hi - emb.lo))

    matched, missing = _match_concepts(q, answer, emb)
    total_w = sum(c.weight for c in q.concepts)
    coverage = sum(c.weight for c in matched) / total_w if total_w else 0.0

    if q.concepts and q.model_answer.strip():
        frac = 0.7 * coverage + 0.3 * sim_score
    elif q.concepts:
        frac = coverage
    else:
        frac = sim_score
    marks = min(q.max_marks, _round_half(frac * q.max_marks))

    mistakes = _detect_mistakes(q, answer, emb)
    mistakes.extend(MistakeOut(type="MISSING_CONCEPT", description=f"Missing concept: {c.name}") for c in missing)

    decisiveness = 0.5 + abs(frac - 0.5)
    confidence = round(_clamp(0.4 * _clamp(ocr_conf) + 0.6 * decisiveness), 3)

    return QuestionResult(
        question_id=q.id, question_number=q.number, answer_text=answer, answer_found=True,
        max_marks=q.max_marks, suggested_marks=marks, similarity=round(sim, 4),
        concept_coverage=round(coverage, 4), matched_concepts=[c.name for c in matched],
        missing_concepts=[c.name for c in missing], mistakes=mistakes,
        feedback=_feedback(q, True, marks, matched, missing, mistakes, sim_score), confidence=confidence)
