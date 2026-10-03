package com.inkgrade.service;

import com.inkgrade.domain.*;
import com.inkgrade.dto.EvaluationDtos.SubmissionDto;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.*;
import com.inkgrade.security.CurrentUser;
import com.inkgrade.storage.FileStorageService;
import com.inkgrade.storage.StoredFile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.util.List;

@Service
public class SubmissionService {
    private final SubmissionRepository submissions;
    private final StudentRepository students;
    private final EvaluationRepository evaluations;
    private final StudentAnswerRepository answers;
    private final ExamService examService;
    private final AccessService access;
    private final FileStorageService storage;
    private final Mapper mapper;
    private final AuditService audit;

    public SubmissionService(SubmissionRepository submissions, StudentRepository students,
                             EvaluationRepository evaluations, StudentAnswerRepository answers,
                             ExamService examService, AccessService access, FileStorageService storage,
                             Mapper mapper, AuditService audit) {
        this.submissions = submissions;
        this.students = students;
        this.evaluations = evaluations;
        this.answers = answers;
        this.examService = examService;
        this.access = access;
        this.storage = storage;
        this.mapper = mapper;
        this.audit = audit;
    }

    private SubmissionDto dto(Submission s) {
        return mapper.submission(s, evaluations.findBySubmissionId(s.getId()).map(Evaluation::getId).orElse(null));
    }

    @Transactional(readOnly = true)
    public List<SubmissionDto> list(Long examId) {
        access.assertExamManage(examService.find(examId));
        return submissions.findByExamIdOrderByUploadedAtDesc(examId).stream().map(this::dto).toList();
    }

    @Transactional
    public SubmissionDto upload(Long examId, Long studentId, MultipartFile file) {
        Exam exam = examService.find(examId);
        access.assertExamManage(exam);
        Student student = students.findById(studentId).orElseThrow(() -> ApiException.notFound("Student"));
        Submission existing = submissions.findByExamIdAndStudentId(examId, studentId).orElse(null);
        if (existing != null) {
            Evaluation ev = evaluations.findBySubmissionId(existing.getId()).orElse(null);
            if (ev != null && ev.getStatus() == EvaluationStatus.FINALIZED) {
                throw ApiException.conflict("A finalized evaluation exists; delete it before re-uploading");
            }
            if (existing.getStatus() == SubmissionStatus.EVALUATING) {
                throw ApiException.conflict("Evaluation in progress for this submission");
            }
        }
        StoredFile f = storage.store(file, "answer-sheets");
        Submission s = existing != null ? existing : new Submission();
        String oldPath = existing != null ? existing.getFilePath() : null;
        s.setExam(exam);
        s.setStudent(student);
        s.setUploadedBy(access.currentTeacherOrNull());
        s.setFilePath(f.relativePath());
        s.setOriginalFileName(f.originalName());
        s.setContentType(f.contentType());
        s.setStatus(SubmissionStatus.UPLOADED);
        s.setOcrText(null);
        s.setOcrConfidence(null);
        s.setErrorMessage(null);
        s.setUploadedAt(java.time.Instant.now());
        submissions.save(s);
        if (existing != null) {
            // replaced sheet invalidates previous AI results
            evaluations.findBySubmissionId(s.getId()).ifPresent(evaluations::delete);
            answers.deleteBySubmissionId(s.getId());
            storage.deleteQuietly(oldPath);
        }
        audit.log("SUBMISSION_UPLOADED", "Submission", s.getId(), "Exam " + examId + ", student " + studentId);
        return dto(s);
    }

    @Transactional(readOnly = true)
    public SubmissionDto get(Long id) {
        Submission s = find(id);
        access.assertExamManage(s.getExam());
        return dto(s);
    }

    @Transactional
    public void delete(Long id) {
        Submission s = find(id);
        access.assertExamManage(s.getExam());
        evaluations.findBySubmissionId(id).ifPresent(evaluations::delete);
        answers.deleteBySubmissionId(id);
        submissions.delete(s);
        submissions.flush();
        storage.deleteQuietly(s.getFilePath());
        audit.log("SUBMISSION_DELETED", "Submission", id, null);
    }

    public record FileRef(Path path, String name, String contentType) {}

    @Transactional(readOnly = true)
    public FileRef file(Long id) {
        Submission s = find(id);
        if (CurrentUser.isStudent()) {
            Evaluation ev = evaluations.findBySubmissionId(id).orElse(null);
            boolean own = s.getStudent().getUser().getId().equals(CurrentUser.get().getId());
            if (!own || ev == null || ev.getStatus() != EvaluationStatus.FINALIZED) {
                throw ApiException.forbidden("You can only view your own published answer sheet");
            }
        } else {
            access.assertExamManage(s.getExam());
        }
        return new FileRef(storage.resolve(s.getFilePath()), s.getOriginalFileName(), s.getContentType());
    }

    Submission find(Long id) {
        return submissions.findById(id).orElseThrow(() -> ApiException.notFound("Submission"));
    }
}
