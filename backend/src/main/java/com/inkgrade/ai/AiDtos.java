package com.inkgrade.ai;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import java.util.List;

public final class AiDtos {
    private AiDtos() {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record OcrResult(String text, double confidence, int pages, String engine) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record ConceptIn(String name, List<String> keywords, double weight) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record QuestionIn(long id, int number, String text, double maxMarks, String modelAnswer,
                             List<ConceptIn> concepts) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record EvaluateRequest(String text, double ocrConfidence, List<QuestionIn> questions) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record MistakeOut(String type, String description, String snippet, Integer startOffset,
                             Integer endOffset, String suggestion) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record QuestionResult(long questionId, int questionNumber, String answerText, boolean answerFound,
                                 double maxMarks, double suggestedMarks, double similarity, double conceptCoverage,
                                 List<String> matchedConcepts, List<String> missingConcepts,
                                 List<MistakeOut> mistakes, String feedback, double confidence) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record EvaluateResponse(List<QuestionResult> results, String embeddingBackend) {}
}
