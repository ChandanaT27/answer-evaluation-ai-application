package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "students")
public class Student extends BaseEntity {
    @OneToOne(optional = false, fetch = FetchType.EAGER)
    @JoinColumn(unique = true)
    private User user;
    @Column(nullable = false, unique = true, length = 40)
    private String rollNumber;
    @Column(length = 60)
    private String className;
}
