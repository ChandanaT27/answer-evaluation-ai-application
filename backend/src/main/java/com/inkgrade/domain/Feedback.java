package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "feedbacks")
public class Feedback extends BaseEntity {
    public enum Source { AI, TEACHER }

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private QuestionEvaluation questionEvaluation;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private Source source;
    @Column(nullable = false, columnDefinition = "TEXT")
    private String text;
    private Instant createdAt = Instant.now();
}
