package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "submissions", uniqueConstraints = @UniqueConstraint(columnNames = {"exam_id", "student_id"}))
public class Submission extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Exam exam;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Student student;
    @ManyToOne(fetch = FetchType.LAZY)
    private Teacher uploadedBy;
    @Column(nullable = false)
    private String filePath;
    @Column(nullable = false)
    private String originalFileName;
    private String contentType;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SubmissionStatus status = SubmissionStatus.UPLOADED;
    @Column(columnDefinition = "TEXT")
    private String ocrText;
    private Double ocrConfidence;
    @Column(length = 1000)
    private String errorMessage;
    private Instant uploadedAt = Instant.now();
}
