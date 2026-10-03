package com.inkgrade.repository;

import com.inkgrade.domain.Exam;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ExamRepository extends JpaRepository<Exam, Long> {
    long countBySubjectId(Long subjectId);
    long countByTeacherId(Long teacherId);

    @Query("""
            select e from Exam e where (:teacherId is null or e.teacher.id = :teacherId)
            and (:subjectId is null or e.subject.id = :subjectId)
            and (:q = '' or lower(e.title) like lower(concat('%', :q, '%')))
            """)
    Page<Exam> search(@Param("teacherId") Long teacherId, @Param("subjectId") Long subjectId,
                      @Param("q") String q, Pageable pageable);

    /** Exams in which the given student has a finalized (published) evaluation. */
    @Query("""
            select distinct e from Exam e, Evaluation ev where ev.submission.exam = e
            and ev.submission.student.id = :studentId and ev.status = com.inkgrade.domain.EvaluationStatus.FINALIZED
            and (:subjectId is null or e.subject.id = :subjectId)
            """)
    java.util.List<Exam> findPublishedForStudent(@Param("studentId") Long studentId, @Param("subjectId") Long subjectId);
}
