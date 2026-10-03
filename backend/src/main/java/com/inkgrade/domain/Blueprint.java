package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.util.ArrayList;
import java.util.List;

@Getter
@Setter
@Entity
@Table(name = "blueprints")
public class Blueprint extends BaseEntity {
    @OneToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(unique = true)
    private Question question;
    @Column(columnDefinition = "TEXT")
    private String modelAnswer;
    private String sourceFileName;
    @OneToMany(mappedBy = "blueprint", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<BlueprintConcept> concepts = new ArrayList<>();
}
