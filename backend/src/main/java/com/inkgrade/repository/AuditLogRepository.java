package com.inkgrade.repository;

import com.inkgrade.domain.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    @Query("""
            select a from AuditLog a where (:q = '' or lower(a.username) like lower(concat('%', :q, '%'))
            or lower(a.action) like lower(concat('%', :q, '%')) or lower(a.entityType) like lower(concat('%', :q, '%')))
            """)
    Page<AuditLog> search(@Param("q") String q, Pageable pageable);
}
