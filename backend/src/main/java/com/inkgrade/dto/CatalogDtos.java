package com.inkgrade.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.LocalDate;
import java.util.List;

public final class CatalogDtos {
    private CatalogDtos() {}

    public record SubjectDto(Long id, String name, String code, String description, boolean active, long examCount) {}

    public record SubjectRequest(@NotBlank @Size(max = 120) String name,
                                 @NotBlank @Size(max = 30) @Pattern(regexp = "[A-Za-z0-9_-]+", message = "letters, digits, - _ only") String code,
                                 @Size(max = 500) String description, Boolean active) {}

    public record ExamDto(Long id, String title, Long subjectId, String subjectName, Long teacherId,
                          String teacherName, LocalDate examDate, String instructions, boolean hasQuestionPaper,
                          String questionPaperName, double totalMarks, int questionCount) {}

    public record ExamRequest(@NotBlank @Size(max = 160) String title, @NotNull Long subjectId, LocalDate examDate,
                              @Size(max = 1000) String instructions) {}

    public record QuestionDto(Long id, int number, String text, double maxMarks, boolean hasBlueprint) {}

    public record QuestionRequest(@Min(1) Integer number, @NotBlank @Size(max = 5000) String text,
                                  @NotNull @DecimalMin(value = "0.0", inclusive = false)
                                  @DecimalMax("1000") Double maxMarks) {}

    public record ConceptDto(Long id, @NotBlank @Size(max = 160) String name, List<@Size(max = 100) String> keywords,
                             @DecimalMin(value = "0.0", inclusive = false) @DecimalMax("100") Double weight) {}

    public record BlueprintDto(Long questionId, String modelAnswer, String sourceFileName, List<ConceptDto> concepts) {}

    public record BlueprintRequest(@Size(max = 20000) String modelAnswer, @Valid List<ConceptDto> concepts) {}
}
