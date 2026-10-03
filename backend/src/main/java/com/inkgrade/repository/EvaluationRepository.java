package com.inkgrade.repository;

import com.inkgrade.domain.Evaluation;
import com.inkgrade.domain.EvaluationStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface EvaluationRepository extends JpaRepository<Evaluation, Long> {
    Optional<Evaluation> findBySubmissionId(Long submissionId);
    long countByStatus(EvaluationStatus status);

    @Query("""
            select ev from Evaluation ev where (:teacherId is null or ev.submission.exam.teacher.id = :teacherId)
            and (:studentId is null or ev.submission.student.id = :studentId)
            and (:examId is null or ev.submission.exam.id = :examId)
            and (:subjectId is null or ev.submission.exam.subject.id = :subjectId)
            and (:status is null or ev.status = :status)
            and ev.evaluatedAt >= :from and ev.evaluatedAt <= :to
            and (:q = '' or lower(ev.submission.student.user.fullName) like lower(concat('%', :q, '%'))
                 or lower(ev.submission.student.rollNumber) like lower(concat('%', :q, '%'))
                 or lower(ev.submission.exam.title) like lower(concat('%', :q, '%')))
            """)
    Page<Evaluation> search(@Param("teacherId") Long teacherId, @Param("studentId") Long studentId,
                            @Param("examId") Long examId, @Param("subjectId") Long subjectId,
                            @Param("status") EvaluationStatus status, @Param("from") Instant from,
                            @Param("to") Instant to, @Param("q") String q, Pageable pageable);

    @Query("""
            select ev from Evaluation ev where ev.submission.student.id = :studentId
            and ev.status = com.inkgrade.domain.EvaluationStatus.FINALIZED order by ev.finalizedAt asc
            """)
    List<Evaluation> findFinalizedForStudent(@Param("studentId") Long studentId);

    @Query("select ev from Evaluation ev where ev.submission.exam.teacher.id = :teacherId")
    List<Evaluation> findByTeacher(@Param("teacherId") Long teacherId);
}
