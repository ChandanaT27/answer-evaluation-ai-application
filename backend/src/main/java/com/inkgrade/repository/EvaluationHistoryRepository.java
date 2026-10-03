package com.inkgrade.repository;

import com.inkgrade.domain.EvaluationHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface EvaluationHistoryRepository extends JpaRepository<EvaluationHistory, Long> {
    List<EvaluationHistory> findByEvaluationIdOrderByChangedAtDesc(Long evaluationId);
}
