package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "subjects")
public class Subject extends BaseEntity {
    @Column(nullable = false, length = 120)
    private String name;
    @Column(nullable = false, unique = true, length = 30)
    private String code;
    @Column(length = 500)
    private String description;
    private boolean active = true;
    @ManyToOne(fetch = FetchType.LAZY)
    private User createdBy;
}
