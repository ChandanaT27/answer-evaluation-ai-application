package com.inkgrade.repository;

import com.inkgrade.domain.Subject;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SubjectRepository extends JpaRepository<Subject, Long> {
    boolean existsByCodeIgnoreCase(String code);

    @Query("""
            select s from Subject s where (:q = '' or lower(s.name) like lower(concat('%', :q, '%'))
            or lower(s.code) like lower(concat('%', :q, '%'))) and (:activeOnly = false or s.active = true)
            """)
    Page<Subject> search(@Param("q") String q, @Param("activeOnly") boolean activeOnly, Pageable pageable);
}
