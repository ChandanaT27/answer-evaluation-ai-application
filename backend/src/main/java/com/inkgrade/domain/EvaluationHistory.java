package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "evaluation_history")
public class EvaluationHistory extends BaseEntity {
    /** Plain id (not an FK) so history survives deletion of the evaluation. */
    @Column(nullable = false)
    private Long evaluationId;
    private Long submissionId;
    private Integer questionNumber;
    @Column(nullable = false, length = 40)
    private String action;
    private Double oldMarks;
    private Double newMarks;
    @Column(length = 1000)
    private String note;
    private Long changedById;
    private String changedByName;
    private Instant changedAt = Instant.now();
}
