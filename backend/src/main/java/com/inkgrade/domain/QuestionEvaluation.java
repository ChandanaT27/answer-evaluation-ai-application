package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

@Getter
@Setter
@Entity
@Table(name = "question_evaluations")
public class QuestionEvaluation extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Evaluation evaluation;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Question question;
    private int questionNumber;
    @Column(columnDefinition = "TEXT")
    private String answerText;
    private boolean answerFound;
    private double maxMarks;
    private double aiMarks;
    /** Null until a teacher overrides; effective marks fall back to aiMarks. */
    private Double finalMarks;
    private double confidence;
    private double similarity;
    private double conceptCoverage;
    @ElementCollection
    @CollectionTable(name = "qe_matched_concepts", joinColumns = @JoinColumn(name = "question_evaluation_id"))
    @Column(name = "concept", length = 200)
    private Set<String> matchedConcepts = new LinkedHashSet<>();
    @ElementCollection
    @CollectionTable(name = "qe_missing_concepts", joinColumns = @JoinColumn(name = "question_evaluation_id"))
    @Column(name = "concept", length = 200)
    private Set<String> missingConcepts = new LinkedHashSet<>();
    private boolean reviewed;
    @OneToMany(mappedBy = "questionEvaluation", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Mistake> mistakes = new ArrayList<>();
    @OneToMany(mappedBy = "questionEvaluation", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("id ASC")
    private List<Feedback> feedbacks = new ArrayList<>();

    public double effectiveMarks() {
        return finalMarks != null ? finalMarks : aiMarks;
    }
}
