package com.inkgrade.service;

import com.inkgrade.domain.*;
import com.inkgrade.dto.EvaluationDtos.*;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.*;
import com.inkgrade.security.AppUserDetails;
import com.inkgrade.security.CurrentUser;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class EvaluationService {
    private final EvaluationRepository evaluations;
    private final SubmissionRepository submissions;
    private final QuestionRepository questions;
    private final BlueprintRepository blueprints;
    private final StudentAnswerRepository answers;
    private final EvaluationHistoryRepository history;
    private final ExamRepository exams;
    private final UserRepository users;
    private final AccessService access;
    private final EvaluationRunner runner;
    private final Mapper mapper;
    private final AuditService audit;
    private final TransactionTemplate tx;

    public EvaluationService(EvaluationRepository evaluations, SubmissionRepository submissions,
                             QuestionRepository questions, BlueprintRepository blueprints,
                             StudentAnswerRepository answers, EvaluationHistoryRepository history,
                             ExamRepository exams, UserRepository users, AccessService access,
                             EvaluationRunner runner, Mapper mapper, AuditService audit,
                             PlatformTransactionManager tm) {
        this.evaluations = evaluations;
        this.submissions = submissions;
        this.questions = questions;
        this.blueprints = blueprints;
        this.answers = answers;
        this.history = history;
        this.exams = exams;
        this.users = users;
        this.access = access;
        this.runner = runner;
        this.mapper = mapper;
        this.audit = audit;
        this.tx = new TransactionTemplate(tm);
    }

    /** Validates and marks the submission as EVALUATING (committed), then runs the pipeline asynchronously. */
    public SubmissionDto start(Long submissionId) {
        AppUserDetails user = CurrentUser.get();
        SubmissionDto dto = tx.execute(s -> {
            Submission sub = submissions.findById(submissionId).orElseThrow(() -> ApiException.notFound("Submission"));
            access.assertExamManage(sub.getExam());
            if (sub.getStatus() == SubmissionStatus.EVALUATING) {
                throw ApiException.conflict("Evaluation already in progress");
            }
            evaluations.findBySubmissionId(submissionId).ifPresent(ev -> {
                if (ev.getStatus() == EvaluationStatus.FINALIZED) {
                    throw ApiException.conflict("Evaluation is finalized; delete it first to re-evaluate");
                }
            });
            List<Question> qs = questions.findByExamIdOrderByNumberAsc(sub.getExam().getId());
            if (qs.isEmpty()) throw ApiException.badRequest("The exam has no questions");
            List<Integer> missing = new ArrayList<>();
            for (Question q : qs) {
                boolean ok = blueprints.findByQuestionId(q.getId())
                        .map(b -> (b.getModelAnswer() != null && !b.getModelAnswer().isBlank()) || !b.getConcepts().isEmpty())
                        .orElse(false);
                if (!ok) missing.add(q.getNumber());
            }
            if (!missing.isEmpty()) {
                throw ApiException.badRequest("Blueprint missing for question(s): " + missing);
            }
            sub.setStatus(SubmissionStatus.EVALUATING);
            sub.setErrorMessage(null);
            audit.log("EVALUATION_STARTED", "Submission", submissionId, null);
            return mapper.submission(sub, null);
        });
        runner.run(submissionId, user.getId(), user.getUsername());
        return dto;
    }

    @Transactional(readOnly = true)
    public PageResponse<EvaluationSummaryDto> search(Long examId, Long subjectId, Long studentId,
                                                     EvaluationStatus status, LocalDate from, LocalDate to,
                                                     String q, int page, int size) {
        Long teacherId = null;
        if (CurrentUser.isStudent()) {
            studentId = access.currentStudent().getId();
            status = EvaluationStatus.FINALIZED;
        } else if (CurrentUser.isTeacher()) {
            teacherId = access.currentTeacher().getId();
        }
        Instant f = from == null ? Instant.parse("1970-01-01T00:00:00Z") : from.atStartOfDay().toInstant(ZoneOffset.UTC);
        Instant t = to == null ? Instant.parse("9999-01-01T00:00:00Z") : to.plusDays(1).atStartOfDay().toInstant(ZoneOffset.UTC).minusMillis(1);
        Pageable p = PageRequest.of(page, Math.min(size, 100), Sort.by(Sort.Direction.DESC, "evaluatedAt"));
        return PageResponse.of(evaluations.search(teacherId, studentId, examId, subjectId, status, f, t,
                UserService.norm(q), p), mapper::summary);
    }

    @Transactional(readOnly = true)
    public EvaluationDetailDto get(Long id) {
        Evaluation ev = find(id);
        access.assertEvaluationView(ev);
        return mapper.detail(ev);
    }

    Evaluation find(Long id) {
        return evaluations.findById(id).orElseThrow(() -> ApiException.notFound("Evaluation"));
    }

    @Transactional
    public EvaluationDetailDto review(Long evaluationId, Long qeId, ReviewRequest r) {
        Evaluation ev = find(evaluationId);
        access.assertStaffEvaluation(ev);
        QuestionEvaluation qe = ev.getQuestionEvaluations().stream().filter(x -> x.getId().equals(qeId)).findFirst()
                .orElseThrow(() -> ApiException.notFound("Question evaluation"));
        if (r.finalMarks() > qe.getMaxMarks()) {
            throw ApiException.badRequest("Marks cannot exceed the maximum of " + qe.getMaxMarks());
        }
        double old = qe.effectiveMarks();
        qe.setFinalMarks(r.finalMarks());
        qe.setReviewed(true);
        if (r.comment() != null && !r.comment().isBlank()) {
            Feedback fb = new Feedback();
            fb.setQuestionEvaluation(qe);
            fb.setSource(Feedback.Source.TEACHER);
            fb.setText(r.comment().trim());
            qe.getFeedbacks().add(fb);
        }
        recalc(ev);
        if (ev.getStatus() == EvaluationStatus.AI_COMPLETED) ev.setStatus(EvaluationStatus.UNDER_REVIEW);
        record(ev, qe.getQuestionNumber(), "MARKS_OVERRIDDEN", old, r.finalMarks(), r.comment());
        audit.log("MARKS_OVERRIDDEN", "Evaluation", evaluationId, "Q" + qe.getQuestionNumber() + ": " + old + " -> " + r.finalMarks());
        evaluations.flush();
        return mapper.detail(ev);
    }

    @Transactional
    public EvaluationDetailDto finalizeEvaluation(Long id) {
        Evaluation ev = find(id);
        access.assertStaffEvaluation(ev);
        recalc(ev);
        ev.getQuestionEvaluations().forEach(q -> q.setReviewed(true));
        ev.setStatus(EvaluationStatus.FINALIZED);
        ev.setFinalizedAt(Instant.now());
        ev.setReviewedBy(users.findById(CurrentUser.get().getId()).orElse(null));
        record(ev, null, "FINALIZED", ev.getAiTotal(), ev.getFinalTotal(), null);
        audit.log("EVALUATION_FINALIZED", "Evaluation", id, "Total " + ev.getFinalTotal() + "/" + ev.getMaxTotal());
        return mapper.detail(ev);
    }

    @Transactional
    public EvaluationDetailDto reopen(Long id) {
        Evaluation ev = find(id);
        access.assertStaffEvaluation(ev);
        if (ev.getStatus() != EvaluationStatus.FINALIZED) throw ApiException.badRequest("Evaluation is not finalized");
        ev.setStatus(EvaluationStatus.UNDER_REVIEW);
        ev.setFinalizedAt(null);
        record(ev, null, "REOPENED", ev.getFinalTotal(), ev.getFinalTotal(), null);
        audit.log("EVALUATION_REOPENED", "Evaluation", id, null);
        return mapper.detail(ev);
    }

    @Transactional
    public void delete(Long id) {
        Evaluation ev = find(id);
        access.assertStaffEvaluation(ev);
        Submission sub = ev.getSubmission();
        record(ev, null, "DELETED", ev.getFinalTotal(), null, null);
        evaluations.delete(ev);
        answers.deleteBySubmissionId(sub.getId());
        sub.setStatus(SubmissionStatus.UPLOADED);
        audit.log("EVALUATION_DELETED", "Evaluation", id, "Submission " + sub.getId());
    }

    @Transactional(readOnly = true)
    public List<HistoryDto> history(Long id) {
        Evaluation ev = find(id);
        access.assertStaffEvaluation(ev);
        return history.findByEvaluationIdOrderByChangedAtDesc(id).stream().map(h -> new HistoryDto(h.getId(),
                h.getQuestionNumber(), h.getAction(), h.getOldMarks(), h.getNewMarks(), h.getNote(),
                h.getChangedByName(), h.getChangedAt())).toList();
    }

    private void recalc(Evaluation ev) {
        ev.setFinalTotal(ev.getQuestionEvaluations().stream().mapToDouble(QuestionEvaluation::effectiveMarks).sum());
    }

    private void record(Evaluation ev, Integer qNo, String action, Double oldM, Double newM, String note) {
        EvaluationHistory h = new EvaluationHistory();
        h.setEvaluationId(ev.getId());
        h.setSubmissionId(ev.getSubmission().getId());
        h.setQuestionNumber(qNo);
        h.setAction(action);
        h.setOldMarks(oldM);
        h.setNewMarks(newM);
        h.setNote(note);
        h.setChangedById(CurrentUser.get().getId());
        h.setChangedByName(CurrentUser.get().getUsername());
        history.save(h);
    }

    @Transactional(readOnly = true)
    public TeacherStatsDto teacherStats() {
        Teacher t = access.currentTeacher();
        List<Evaluation> evs = evaluations.findByTeacher(t.getId());
        long finalized = evs.stream().filter(e -> e.getStatus() == EvaluationStatus.FINALIZED).count();
        long pending = evs.size() - finalized;
        double avg = evs.stream().filter(e -> e.getMaxTotal() > 0).mapToDouble(e -> e.getFinalTotal() / e.getMaxTotal() * 100)
                .average().orElse(0);
        long subs = exams.search(t.getId(), null, "", PageRequest.of(0, 1000)).stream()
                .mapToLong(e -> submissions.findByExamIdOrderByUploadedAtDesc(e.getId()).size()).sum();
        return new TeacherStatsDto(exams.countByTeacherId(t.getId()), subs, evs.size(), pending, finalized,
                Math.round(avg * 100) / 100.0);
    }

    @Transactional(readOnly = true)
    public StudentPerformanceDto performance() {
        Student s = access.currentStudent();
        List<Evaluation> evs = evaluations.findFinalizedForStudent(s.getId());
        List<ExamPerformance> perf = evs.stream().map(e -> new ExamPerformance(e.getId(),
                e.getSubmission().getExam().getTitle(), e.getSubmission().getExam().getSubject().getName(),
                pct(e.getFinalTotal(), e.getMaxTotal()), e.getFinalTotal(), e.getMaxTotal(), e.getFinalizedAt())).toList();
        Map<String, List<ExamPerformance>> bySubject = new LinkedHashMap<>();
        perf.forEach(p -> bySubject.computeIfAbsent(p.subjectName(), k -> new ArrayList<>()).add(p));
        List<SubjectAverage> subjects = bySubject.entrySet().stream().map(en -> new SubjectAverage(en.getKey(),
                Math.round(en.getValue().stream().mapToDouble(ExamPerformance::percentage).average().orElse(0) * 100) / 100.0,
                en.getValue().size())).toList();
        double overall = perf.stream().mapToDouble(ExamPerformance::percentage).average().orElse(0);
        return new StudentPerformanceDto(perf, subjects, Math.round(overall * 100) / 100.0);
    }

    private static double pct(double v, double max) {
        return max > 0 ? Math.round(v / max * 10000.0) / 100.0 : 0;
    }
}
