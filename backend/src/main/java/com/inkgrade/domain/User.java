package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "users")
public class User extends BaseEntity {
    @Column(nullable = false, unique = true, length = 60)
    private String username;
    @Column(nullable = false, unique = true, length = 120)
    private String email;
    @Column(nullable = false)
    private String passwordHash;
    @Column(nullable = false, length = 120)
    private String fullName;
    @ManyToOne(fetch = FetchType.EAGER, optional = false)
    private Role role;
    private boolean enabled = true;
    private Instant createdAt = Instant.now();
    private Instant lastLoginAt;
}
