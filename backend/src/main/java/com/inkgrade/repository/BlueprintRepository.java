package com.inkgrade.repository;

import com.inkgrade.domain.Blueprint;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface BlueprintRepository extends JpaRepository<Blueprint, Long> {
    Optional<Blueprint> findByQuestionId(Long questionId);
    List<Blueprint> findByQuestionExamId(Long examId);
}
