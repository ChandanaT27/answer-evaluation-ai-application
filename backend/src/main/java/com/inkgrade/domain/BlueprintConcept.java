package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "blueprint_concepts")
public class BlueprintConcept extends BaseEntity {
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private Blueprint blueprint;
    @Column(nullable = false, length = 160)
    private String name;
    /** Comma separated synonyms / alternative phrasings. */
    @Column(length = 1000)
    private String keywords;
    @Column(nullable = false)
    private double weight = 1.0;
}
