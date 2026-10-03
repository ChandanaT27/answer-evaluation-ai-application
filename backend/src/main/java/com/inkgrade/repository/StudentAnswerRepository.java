package com.inkgrade.repository;

import com.inkgrade.domain.StudentAnswer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;

import java.util.List;

public interface StudentAnswerRepository extends JpaRepository<StudentAnswer, Long> {
    List<StudentAnswer> findBySubmissionId(Long submissionId);

    @Modifying
    void deleteBySubmissionId(Long submissionId);
}
