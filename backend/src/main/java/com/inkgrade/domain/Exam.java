package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;
import java.time.LocalDate;

@Getter
@Setter
@Entity
@Table(name = "exams")
public class Exam extends BaseEntity {
    @Column(nullable = false, length = 160)
    private String title;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Subject subject;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Teacher teacher;
    private LocalDate examDate;
    @Column(length = 1000)
    private String instructions;
    private String questionPaperPath;
    private String questionPaperName;
    private Instant createdAt = Instant.now();
}
