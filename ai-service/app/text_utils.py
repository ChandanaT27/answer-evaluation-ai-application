from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import List, Set

STOPWORDS = set("""a an the of to in on at for and or but is are was were be been being it its this that these those
with as by from into than then so such which who whom whose what when where why how can could may might will would shall
should do does did done have has had not no nor also very more most any each other some their there they them we our you your
he she his her i me my""".split())

_SUFFIXES = ("ization", "ations", "ation", "ingly", "ments", "ment", "ities", "ity", "ness", "ing", "ies", "ied",
             "ers", "est", "ed", "es", "er", "ly", "s")


def stem(word: str) -> str:
    w = word.lower()
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            if suf in ("ies", "ied"):
                w += "y"
            break
    return w


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9']*", text.lower())


def content_stems(text: str) -> List[str]:
    return [stem(t) for t in tokenize(text) if t not in STOPWORDS]


def stem_set(text: str) -> Set[str]:
    return set(content_stems(text))


def fuzzy_eq(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) < 5 or len(b) < 5:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def split_sentences(text: str) -> List[tuple]:
    """Return (sentence, start, end) tuples."""
    out = []
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s = m.group().strip()
        if s:
            out.append((s, m.start(), m.end()))
    return out
