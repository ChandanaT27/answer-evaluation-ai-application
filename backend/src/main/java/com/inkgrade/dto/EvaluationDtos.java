package com.inkgrade.dto;

import com.inkgrade.domain.EvaluationStatus;
import com.inkgrade.domain.MistakeType;
import com.inkgrade.domain.SubmissionStatus;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.Instant;
import java.util.List;

public final class EvaluationDtos {
    private EvaluationDtos() {}

    public record SubmissionDto(Long id, Long examId, String examTitle, Long studentId, String studentName,
                                String rollNumber, String fileName, SubmissionStatus status, Instant uploadedAt,
                                String errorMessage, Double ocrConfidence, Long evaluationId) {}

    public record EvaluationSummaryDto(Long id, Long submissionId, Long examId, String examTitle, Long subjectId,
                                       String subjectName, Long studentId, String studentName, String rollNumber,
                                       EvaluationStatus status, double maxTotal, double aiTotal, double finalTotal,
                                       double percentage, Instant evaluatedAt, Instant finalizedAt) {}

    public record MistakeDto(Long id, MistakeType type, String description, String snippet, Integer startOffset,
                             Integer endOffset, String suggestion) {}

    public record FeedbackDto(Long id, String source, String text, Instant createdAt) {}

    public record QuestionEvaluationDto(Long id, Long questionId, int questionNumber, String questionText,
                                        String answerText, boolean answerFound, double maxMarks, double aiMarks,
                                        Double finalMarks, double effectiveMarks, double confidence,
                                        double similarity, double conceptCoverage, List<String> matchedConcepts,
                                        List<String> missingConcepts, boolean reviewed, List<MistakeDto> mistakes,
                                        List<FeedbackDto> feedback) {}

    public record EvaluationDetailDto(EvaluationSummaryDto summary, String embeddingBackend, String reviewedBy,
                                      List<QuestionEvaluationDto> questions) {}

    public record ReviewRequest(@NotNull @DecimalMin("0.0") Double finalMarks, @Size(max = 2000) String comment) {}

    public record HistoryDto(Long id, Integer questionNumber, String action, Double oldMarks, Double newMarks,
                             String note, String changedBy, Instant changedAt) {}

    public record AdminStatsDto(long students, long teachers, long admins, long subjects, long exams,
                                long submissions, long evaluations, long finalizedEvaluations, long auditEvents) {}

    public record TeacherStatsDto(long exams, long submissions, long evaluations, long pendingReview,
                                  long finalized, double averagePercentage) {}

    public record ExamPerformance(Long evaluationId, String examTitle, String subjectName, double percentage,
                                  double marks, double maxMarks, Instant date) {}

    public record SubjectAverage(String subjectName, double averagePercentage, long exams) {}

    public record StudentPerformanceDto(List<ExamPerformance> exams, List<SubjectAverage> subjects,
                                        double overallPercentage) {}

    public record AuditLogDto(Long id, String username, String action, String entityType, Long entityId,
                              String details, String ipAddress, Instant createdAt) {}
}
