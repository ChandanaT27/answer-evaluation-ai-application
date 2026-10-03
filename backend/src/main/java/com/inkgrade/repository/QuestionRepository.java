package com.inkgrade.repository;

import com.inkgrade.domain.Question;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface QuestionRepository extends JpaRepository<Question, Long> {
    List<Question> findByExamIdOrderByNumberAsc(Long examId);
    boolean existsByExamIdAndNumber(Long examId, int number);

    @Query("select coalesce(sum(q.maxMarks), 0) from Question q where q.exam.id = :examId")
    double sumMarks(Long examId);
}
