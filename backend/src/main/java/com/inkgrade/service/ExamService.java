package com.inkgrade.service;

import com.inkgrade.domain.Exam;
import com.inkgrade.domain.Subject;
import com.inkgrade.dto.CatalogDtos.*;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.ExamRepository;
import com.inkgrade.repository.QuestionRepository;
import com.inkgrade.repository.SubjectRepository;
import com.inkgrade.security.CurrentUser;
import com.inkgrade.storage.FileStorageService;
import com.inkgrade.storage.StoredFile;
import org.springframework.data.domain.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.util.List;

@Service
public class ExamService {
    private final ExamRepository exams;
    private final SubjectRepository subjects;
    private final QuestionRepository questions;
    private final AccessService access;
    private final FileStorageService storage;
    private final Mapper mapper;
    private final AuditService audit;

    public ExamService(ExamRepository exams, SubjectRepository subjects, QuestionRepository questions,
                       AccessService access, FileStorageService storage, Mapper mapper, AuditService audit) {
        this.exams = exams;
        this.subjects = subjects;
        this.questions = questions;
        this.access = access;
        this.storage = storage;
        this.mapper = mapper;
        this.audit = audit;
    }

    ExamDto dto(Exam e) {
        var qs = questions.findByExamIdOrderByNumberAsc(e.getId());
        return mapper.exam(e, qs.stream().mapToDouble(q -> q.getMaxMarks()).sum(), qs.size());
    }

    @Transactional(readOnly = true)
    public PageResponse<ExamDto> list(Long subjectId, String q, int page, int size) {
        Pageable p = PageRequest.of(page, Math.min(size, 100), Sort.by(Sort.Direction.DESC, "createdAt"));
        if (CurrentUser.isStudent()) {
            String needle = UserService.norm(q).toLowerCase();
            List<Exam> list = exams.findPublishedForStudent(access.currentStudent().getId(), subjectId).stream()
                    .filter(e -> needle.isEmpty() || e.getTitle().toLowerCase().contains(needle)).toList();
            return PageResponse.of(new PageImpl<>(list, p, list.size()), this::dto);
        }
        Long teacherId = CurrentUser.isTeacher() ? access.currentTeacher().getId() : null;
        return PageResponse.of(exams.search(teacherId, subjectId, UserService.norm(q), p), this::dto);
    }

    @Transactional(readOnly = true)
    public ExamDto get(Long id) {
        Exam e = find(id);
        access.assertExamManage(e);
        return dto(e);
    }

    @Transactional
    public ExamDto create(ExamRequest r) {
        Subject s = subjects.findById(r.subjectId()).orElseThrow(() -> ApiException.notFound("Subject"));
        if (!s.isActive()) throw ApiException.badRequest("Subject is inactive");
        Exam e = new Exam();
        e.setTeacher(access.currentTeacher());
        apply(e, r, s);
        exams.save(e);
        audit.log("EXAM_CREATED", "Exam", e.getId(), e.getTitle());
        return dto(e);
    }

    @Transactional
    public ExamDto update(Long id, ExamRequest r) {
        Exam e = find(id);
        access.assertExamManage(e);
        Subject s = subjects.findById(r.subjectId()).orElseThrow(() -> ApiException.notFound("Subject"));
        apply(e, r, s);
        audit.log("EXAM_UPDATED", "Exam", id, e.getTitle());
        return dto(e);
    }

    @Transactional
    public void delete(Long id) {
        Exam e = find(id);
        access.assertExamManage(e);
        String paper = e.getQuestionPaperPath();
        exams.delete(e);
        exams.flush();
        storage.deleteQuietly(paper);
        audit.log("EXAM_DELETED", "Exam", id, e.getTitle());
    }

    @Transactional
    public ExamDto uploadQuestionPaper(Long id, MultipartFile file) {
        Exam e = find(id);
        access.assertExamManage(e);
        StoredFile f = storage.store(file, "question-papers");
        String old = e.getQuestionPaperPath();
        e.setQuestionPaperPath(f.relativePath());
        e.setQuestionPaperName(f.originalName());
        storage.deleteQuietly(old);
        audit.log("QUESTION_PAPER_UPLOADED", "Exam", id, f.originalName());
        return dto(e);
    }

    @Transactional(readOnly = true)
    public Path questionPaper(Long id) {
        Exam e = find(id);
        access.assertExamManage(e);
        if (e.getQuestionPaperPath() == null) throw ApiException.notFound("Question paper");
        return storage.resolve(e.getQuestionPaperPath());
    }

    @Transactional(readOnly = true)
    public String questionPaperName(Long id) {
        return find(id).getQuestionPaperName();
    }

    private void apply(Exam e, ExamRequest r, Subject s) {
        e.setTitle(r.title().trim());
        e.setSubject(s);
        e.setExamDate(r.examDate());
        e.setInstructions(r.instructions());
    }

    Exam find(Long id) {
        return exams.findById(id).orElseThrow(() -> ApiException.notFound("Exam"));
    }
}
