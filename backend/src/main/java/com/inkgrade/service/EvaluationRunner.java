package com.inkgrade.service;

import com.inkgrade.ai.AiClient;
import com.inkgrade.ai.AiDtos;
import com.inkgrade.domain.*;
import com.inkgrade.repository.*;
import com.inkgrade.storage.FileStorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.nio.file.Path;
import java.util.*;
import java.util.stream.Collectors;

/** Runs OCR + AI evaluation in the background and persists the result. */
@Component
public class EvaluationRunner {
    private static final Logger log = LoggerFactory.getLogger(EvaluationRunner.class);

    private final SubmissionRepository submissions;
    private final QuestionRepository questions;
    private final BlueprintRepository blueprints;
    private final EvaluationRepository evaluations;
    private final StudentAnswerRepository answers;
    private final EvaluationHistoryRepository history;
    private final AiClient ai;
    private final FileStorageService storage;
    private final AuditService audit;
    private final TransactionTemplate tx;

    public EvaluationRunner(SubmissionRepository submissions, QuestionRepository questions,
                            BlueprintRepository blueprints, EvaluationRepository evaluations,
                            StudentAnswerRepository answers, EvaluationHistoryRepository history, AiClient ai,
                            FileStorageService storage, AuditService audit, PlatformTransactionManager tm) {
        this.submissions = submissions;
        this.questions = questions;
        this.blueprints = blueprints;
        this.evaluations = evaluations;
        this.answers = answers;
        this.history = history;
        this.ai = ai;
        this.storage = storage;
        this.audit = audit;
        this.tx = new TransactionTemplate(tm);
    }

    private record Prep(String filePath, String fileName, String ocrText, Double ocrConfidence,
                        List<AiDtos.QuestionIn> questions) {}

    @Async
    public void run(Long submissionId, Long userId, String username) {
        try {
            Prep prep = tx.execute(s -> prepare(submissionId));
            String text = prep.ocrText();
            double conf = prep.ocrConfidence() == null ? 1.0 : prep.ocrConfidence();
            if (text == null) {
                Path file = storage.resolve(prep.filePath());
                AiDtos.OcrResult ocr = ai.ocr(file, prep.fileName());
                text = ocr.text() == null ? "" : ocr.text();
                conf = ocr.confidence();
                String t = text;
                double c = conf;
                tx.executeWithoutResult(s -> submissions.findById(submissionId).ifPresent(sub -> {
                    sub.setOcrText(t);
                    sub.setOcrConfidence(c);
                }));
            }
            if (text.isBlank()) {
                throw new IllegalStateException("No text could be recognised in the answer sheet");
            }
            AiDtos.EvaluateResponse resp = ai.evaluate(new AiDtos.EvaluateRequest(text, conf, prep.questions()));
            Long evalId = tx.execute(s -> persist(submissionId, resp, userId, username));
            audit.logAs(userId, username, "EVALUATION_COMPLETED", "Evaluation", evalId, "Submission " + submissionId);
        } catch (Exception e) {
            log.error("Evaluation of submission {} failed", submissionId, e);
            String msg = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
            String shortMsg = msg.length() > 900 ? msg.substring(0, 900) : msg;
            tx.executeWithoutResult(s -> submissions.findById(submissionId).ifPresent(sub -> {
                sub.setStatus(SubmissionStatus.FAILED);
                sub.setErrorMessage(shortMsg);
            }));
            audit.logAs(userId, username, "EVALUATION_FAILED", "Submission", submissionId, shortMsg);
        }
    }

    private Prep prepare(Long submissionId) {
        Submission s = submissions.findById(submissionId).orElseThrow();
        List<AiDtos.QuestionIn> qs = new ArrayList<>();
        for (Question q : questions.findByExamIdOrderByNumberAsc(s.getExam().getId())) {
            Blueprint b = blueprints.findByQuestionId(q.getId()).orElseThrow();
            List<AiDtos.ConceptIn> concepts = b.getConcepts().stream()
                    .map(c -> new AiDtos.ConceptIn(c.getName(), Mapper.splitKeywords(c.getKeywords()), c.getWeight()))
                    .toList();
            qs.add(new AiDtos.QuestionIn(q.getId(), q.getNumber(), q.getText(), q.getMaxMarks(),
                    b.getModelAnswer() == null ? "" : b.getModelAnswer(), concepts));
        }
        return new Prep(s.getFilePath(), s.getOriginalFileName(), s.getOcrText(), s.getOcrConfidence(), qs);
    }

    private Long persist(Long submissionId, AiDtos.EvaluateResponse resp, Long userId, String username) {
        Submission sub = submissions.findById(submissionId).orElseThrow();
        evaluations.findBySubmissionId(submissionId).ifPresent(old -> {
            evaluations.delete(old);
            evaluations.flush();
        });
        Map<Long, Question> byId = questions.findByExamIdOrderByNumberAsc(sub.getExam().getId()).stream()
                .collect(Collectors.toMap(Question::getId, q -> q));
        Map<Long, StudentAnswer> existing = answers.findBySubmissionId(submissionId).stream()
                .collect(Collectors.toMap(a -> a.getQuestion().getId(), a -> a));

        Evaluation ev = new Evaluation();
        ev.setSubmission(sub);
        ev.setEmbeddingBackend(resp.embeddingBackend());
        double max = byId.values().stream().mapToDouble(Question::getMaxMarks).sum();
        double total = 0;
        for (AiDtos.QuestionResult r : resp.results()) {
            Question q = byId.get(r.questionId());
            if (q == null) continue;
            StudentAnswer sa = existing.getOrDefault(q.getId(), new StudentAnswer());
            sa.setSubmission(sub);
            sa.setQuestion(q);
            sa.setAnswerText(r.answerText());
            sa.setFound(r.answerFound());
            answers.save(sa);

            QuestionEvaluation qe = new QuestionEvaluation();
            qe.setEvaluation(ev);
            qe.setQuestion(q);
            qe.setQuestionNumber(q.getNumber());
            qe.setAnswerText(r.answerText());
            qe.setAnswerFound(r.answerFound());
            qe.setMaxMarks(q.getMaxMarks());
            double marks = Math.max(0, Math.min(q.getMaxMarks(), r.suggestedMarks()));
            qe.setAiMarks(marks);
            qe.setConfidence(Math.max(0, Math.min(1, r.confidence())));
            qe.setSimilarity(r.similarity());
            qe.setConceptCoverage(r.conceptCoverage());
            if (r.matchedConcepts() != null) qe.getMatchedConcepts().addAll(r.matchedConcepts());
            if (r.missingConcepts() != null) qe.getMissingConcepts().addAll(r.missingConcepts());
            if (r.mistakes() != null) {
                for (AiDtos.MistakeOut m : r.mistakes()) {
                    MistakeType type;
                    try {
                        type = MistakeType.valueOf(m.type());
                    } catch (IllegalArgumentException | NullPointerException e) {
                        continue;
                    }
                    if (type == MistakeType.MISSING_CONCEPT) continue; // stored as missingConcepts
                    Mistake mk = new Mistake();
                    mk.setQuestionEvaluation(qe);
                    mk.setType(type);
                    mk.setDescription(trim(m.description(), 500));
                    mk.setSnippet(trim(m.snippet(), 1000));
                    mk.setStartOffset(m.startOffset());
                    mk.setEndOffset(m.endOffset());
                    mk.setSuggestion(trim(m.suggestion(), 300));
                    qe.getMistakes().add(mk);
                }
            }
            if (r.feedback() != null && !r.feedback().isBlank()) {
                Feedback fb = new Feedback();
                fb.setQuestionEvaluation(qe);
                fb.setSource(Feedback.Source.AI);
                fb.setText(r.feedback());
                qe.getFeedbacks().add(fb);
            }
            ev.getQuestionEvaluations().add(qe);
            total += marks;
        }
        ev.setMaxTotal(max);
        ev.setAiTotal(total);
        ev.setFinalTotal(total);
        evaluations.save(ev);

        sub.setStatus(SubmissionStatus.EVALUATED);
        sub.setErrorMessage(null);

        EvaluationHistory h = new EvaluationHistory();
        h.setEvaluationId(ev.getId());
        h.setSubmissionId(submissionId);
        h.setAction("AI_EVALUATED");
        h.setNewMarks(total);
        h.setNote("Embedding backend: " + resp.embeddingBackend());
        h.setChangedById(userId);
        h.setChangedByName(username);
        history.save(h);
        return ev.getId();
    }

    private static String trim(String s, int n) {
        return s == null ? null : s.length() > n ? s.substring(0, n) : s;
    }
}
