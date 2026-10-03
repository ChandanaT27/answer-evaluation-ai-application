package com.inkgrade.service;

import com.inkgrade.domain.*;
import com.inkgrade.dto.CatalogDtos.*;
import com.inkgrade.dto.EvaluationDtos.*;
import com.inkgrade.dto.UserDtos.*;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Component
public class Mapper {

    public UserDto user(User u, Student s, Teacher t) {
        return new UserDto(u.getId(), u.getUsername(), u.getEmail(), u.getFullName(), u.getRole().getName(),
                u.isEnabled(), s == null ? null : s.getRollNumber(), s == null ? null : s.getClassName(),
                t == null ? null : t.getEmployeeId(), t == null ? null : t.getDepartment(),
                u.getRole().getPermissions(), u.getCreatedAt(), u.getLastLoginAt());
    }

    public StudentDto student(Student s) {
        return new StudentDto(s.getId(), s.getUser().getId(), s.getUser().getFullName(), s.getRollNumber(),
                s.getClassName());
    }

    public SubjectDto subject(Subject s, long examCount) {
        return new SubjectDto(s.getId(), s.getName(), s.getCode(), s.getDescription(), s.isActive(), examCount);
    }

    public ExamDto exam(Exam e, double totalMarks, int questionCount) {
        return new ExamDto(e.getId(), e.getTitle(), e.getSubject().getId(), e.getSubject().getName(),
                e.getTeacher().getId(), e.getTeacher().getUser().getFullName(), e.getExamDate(), e.getInstructions(),
                e.getQuestionPaperPath() != null, e.getQuestionPaperName(), totalMarks, questionCount);
    }

    public QuestionDto question(Question q, boolean hasBlueprint) {
        return new QuestionDto(q.getId(), q.getNumber(), q.getText(), q.getMaxMarks(), hasBlueprint);
    }

    public BlueprintDto blueprint(Blueprint b) {
        List<ConceptDto> cs = b.getConcepts().stream()
                .map(c -> new ConceptDto(c.getId(), c.getName(), splitKeywords(c.getKeywords()), c.getWeight())).toList();
        return new BlueprintDto(b.getQuestion().getId(), b.getModelAnswer(), b.getSourceFileName(), cs);
    }

    public static List<String> splitKeywords(String s) {
        if (s == null || s.isBlank()) return List.of();
        return Arrays.stream(s.split(",")).map(String::trim).filter(x -> !x.isEmpty()).toList();
    }

    public SubmissionDto submission(Submission s, Long evaluationId) {
        return new SubmissionDto(s.getId(), s.getExam().getId(), s.getExam().getTitle(), s.getStudent().getId(),
                s.getStudent().getUser().getFullName(), s.getStudent().getRollNumber(), s.getOriginalFileName(),
                s.getStatus(), s.getUploadedAt(), s.getErrorMessage(), s.getOcrConfidence(), evaluationId);
    }

    public EvaluationSummaryDto summary(Evaluation ev) {
        Submission s = ev.getSubmission();
        Exam e = s.getExam();
        double total = ev.getFinalTotal();
        double pct = ev.getMaxTotal() > 0 ? Math.round(total / ev.getMaxTotal() * 10000.0) / 100.0 : 0;
        return new EvaluationSummaryDto(ev.getId(), s.getId(), e.getId(), e.getTitle(), e.getSubject().getId(),
                e.getSubject().getName(), s.getStudent().getId(), s.getStudent().getUser().getFullName(),
                s.getStudent().getRollNumber(), ev.getStatus(), ev.getMaxTotal(), ev.getAiTotal(), total, pct,
                ev.getEvaluatedAt(), ev.getFinalizedAt());
    }

    public QuestionEvaluationDto questionEvaluation(QuestionEvaluation q) {
        List<MistakeDto> mistakes = q.getMistakes().stream()
                .map(m -> new MistakeDto(m.getId(), m.getType(), m.getDescription(), m.getSnippet(), m.getStartOffset(),
                        m.getEndOffset(), m.getSuggestion())).toList();
        List<FeedbackDto> fb = q.getFeedbacks().stream()
                .map(f -> new FeedbackDto(f.getId(), f.getSource().name(), f.getText(), f.getCreatedAt())).toList();
        return new QuestionEvaluationDto(q.getId(), q.getQuestion().getId(), q.getQuestionNumber(),
                q.getQuestion().getText(), q.getAnswerText(), q.isAnswerFound(), q.getMaxMarks(), q.getAiMarks(),
                q.getFinalMarks(), q.effectiveMarks(), q.getConfidence(), q.getSimilarity(), q.getConceptCoverage(),
                new ArrayList<>(q.getMatchedConcepts()), new ArrayList<>(q.getMissingConcepts()), q.isReviewed(),
                mistakes, fb);
    }

    public EvaluationDetailDto detail(Evaluation ev) {
        return new EvaluationDetailDto(summary(ev), ev.getEmbeddingBackend(),
                ev.getReviewedBy() == null ? null : ev.getReviewedBy().getFullName(),
                ev.getQuestionEvaluations().stream().map(this::questionEvaluation).toList());
    }
}
