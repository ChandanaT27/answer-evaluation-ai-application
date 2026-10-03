package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "questions", uniqueConstraints = @UniqueConstraint(columnNames = {"exam_id", "number"}))
public class Question extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Exam exam;
    @Column(nullable = false)
    private int number;
    @Column(nullable = false, columnDefinition = "TEXT")
    private String text;
    @Column(nullable = false)
    private double maxMarks;
}
