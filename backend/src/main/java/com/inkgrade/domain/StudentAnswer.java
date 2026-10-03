package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "student_answers", uniqueConstraints = @UniqueConstraint(columnNames = {"submission_id", "question_id"}))
public class StudentAnswer extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Submission submission;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Question question;
    @Column(columnDefinition = "TEXT")
    private String answerText;
    private boolean found;
}
