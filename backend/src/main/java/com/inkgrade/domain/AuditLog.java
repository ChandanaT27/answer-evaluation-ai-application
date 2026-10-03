package com.inkgrade.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "audit_logs", indexes = @Index(columnList = "createdAt"))
public class AuditLog extends BaseEntity {
    private Long userId;
    @Column(length = 60)
    private String username;
    @Column(nullable = false, length = 60)
    private String action;
    @Column(length = 60)
    private String entityType;
    private Long entityId;
    @Column(length = 1000)
    private String details;
    @Column(length = 64)
    private String ipAddress;
    @Column(nullable = false)
    private Instant createdAt = Instant.now();
}
