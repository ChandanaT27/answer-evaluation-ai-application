package com.inkgrade.repository;

import com.inkgrade.domain.Student;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface StudentRepository extends JpaRepository<Student, Long> {
    Optional<Student> findByUserId(Long userId);
    boolean existsByRollNumberIgnoreCase(String rollNumber);

    @Query("""
            select s from Student s where :q = '' or lower(s.rollNumber) like lower(concat('%', :q, '%'))
            or lower(s.user.fullName) like lower(concat('%', :q, '%'))
            """)
    Page<Student> search(@Param("q") String q, Pageable pageable);
}
