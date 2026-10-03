package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Getter
@Setter
@Entity
@Table(name = "evaluations")
public class Evaluation extends BaseEntity {
    @OneToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(unique = true)
    private Submission submission;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private EvaluationStatus status = EvaluationStatus.AI_COMPLETED;
    private double maxTotal;
    private double aiTotal;
    /** Sum of effective (teacher override, else AI) marks; refreshed on every review change. */
    private double finalTotal;
    private String embeddingBackend;
    private Instant evaluatedAt = Instant.now();
    private Instant finalizedAt;
    @ManyToOne(fetch = FetchType.LAZY)
    private User reviewedBy;
    @OneToMany(mappedBy = "evaluation", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("questionNumber ASC")
    private List<QuestionEvaluation> questionEvaluations = new ArrayList<>();
}
