package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "teachers")
public class Teacher extends BaseEntity {
    @OneToOne(optional = false, fetch = FetchType.EAGER)
    @JoinColumn(unique = true)
    private User user;
    @Column(length = 40)
    private String employeeId;
    @Column(length = 80)
    private String department;
}
