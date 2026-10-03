package com.inkgrade.service;

import com.inkgrade.domain.*;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.StudentRepository;
import com.inkgrade.repository.TeacherRepository;
import com.inkgrade.security.CurrentUser;
import org.springframework.stereotype.Service;

/** Centralised ownership checks so controllers/services never leak data across users. */
@Service
public class AccessService {
    private final TeacherRepository teachers;
    private final StudentRepository students;

    public AccessService(TeacherRepository teachers, StudentRepository students) {
        this.teachers = teachers;
        this.students = students;
    }

    public Teacher currentTeacher() {
        return teachers.findByUserId(CurrentUser.get().getId())
                .orElseThrow(() -> ApiException.forbidden("Teacher profile required"));
    }

    public Teacher currentTeacherOrNull() {
        return teachers.findByUserId(CurrentUser.get().getId()).orElse(null);
    }

    public Student currentStudent() {
        return students.findByUserId(CurrentUser.get().getId())
                .orElseThrow(() -> ApiException.forbidden("Student profile required"));
    }

    /** Admins may access everything; teachers only exams they own. */
    public void assertExamManage(Exam exam) {
        if (CurrentUser.isAdmin()) return;
        if (CurrentUser.isTeacher() && exam.getTeacher().getUser().getId().equals(CurrentUser.get().getId())) return;
        throw ApiException.forbidden("You do not own this exam");
    }

    /** Teacher/admin view of an evaluation, or the owning student once it is finalized. */
    public void assertEvaluationView(Evaluation ev) {
        Submission s = ev.getSubmission();
        if (CurrentUser.isStudent()) {
            boolean own = s.getStudent().getUser().getId().equals(CurrentUser.get().getId());
            if (!own || ev.getStatus() != EvaluationStatus.FINALIZED) {
                throw ApiException.forbidden("You can only view your own published results");
            }
            return;
        }
        assertExamManage(s.getExam());
    }

    public void assertStaffEvaluation(Evaluation ev) {
        if (CurrentUser.isStudent()) throw ApiException.forbidden("Not allowed");
        assertExamManage(ev.getSubmission().getExam());
    }
}
