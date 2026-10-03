package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "mistakes")
public class Mistake extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private QuestionEvaluation questionEvaluation;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private MistakeType type;
    @Column(nullable = false, length = 500)
    private String description;
    @Column(length = 1000)
    private String snippet;
    private Integer startOffset;
    private Integer endOffset;
    @Column(length = 300)
    private String suggestion;
}
