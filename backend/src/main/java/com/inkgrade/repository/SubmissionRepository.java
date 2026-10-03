package com.inkgrade.repository;

import com.inkgrade.domain.Submission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface SubmissionRepository extends JpaRepository<Submission, Long> {
    List<Submission> findByExamIdOrderByUploadedAtDesc(Long examId);
    Optional<Submission> findByExamIdAndStudentId(Long examId, Long studentId);
}
