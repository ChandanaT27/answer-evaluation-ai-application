package com.inkgrade.web;

import com.inkgrade.dto.CatalogDtos.*;
import com.inkgrade.dto.EvaluationDtos.StudentPerformanceDto;
import com.inkgrade.dto.EvaluationDtos.TeacherStatsDto;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.dto.UserDtos.StudentDto;
import com.inkgrade.service.*;
import jakarta.validation.Valid;
import org.springframework.core.io.PathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.util.List;

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final SubjectService subjects;
    private final ExamService exams;
    private final QuestionService questions;
    private final UserService users;
    private final EvaluationService evaluations;

    public CatalogController(SubjectService subjects, ExamService exams, QuestionService questions,
                             UserService users, EvaluationService evaluations) {
        this.subjects = subjects;
        this.exams = exams;
        this.questions = questions;
        this.users = users;
        this.evaluations = evaluations;
    }

    // ---- subjects
    @GetMapping("/subjects")
    public PageResponse<SubjectDto> subjects(@RequestParam(required = false) String q,
                                             @RequestParam(defaultValue = "false") boolean activeOnly,
                                             @RequestParam(defaultValue = "0") int page,
                                             @RequestParam(defaultValue = "50") int size) {
        return subjects.list(q, activeOnly, Math.max(page, 0), Math.max(size, 1));
    }

    @PostMapping("/subjects")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAuthority('SUBJECT_MANAGE')")
    public SubjectDto createSubject(@Valid @RequestBody SubjectRequest r) {
        return subjects.create(r);
    }

    @PutMapping("/subjects/{id}")
    @PreAuthorize("hasAuthority('SUBJECT_MANAGE')")
    public SubjectDto updateSubject(@PathVariable Long id, @Valid @RequestBody SubjectRequest r) {
        return subjects.update(id, r);
    }

    @DeleteMapping("/subjects/{id}")
    @PreAuthorize("hasAuthority('SUBJECT_MANAGE')")
    public ResponseEntity<Void> deleteSubject(@PathVariable Long id) {
        subjects.delete(id);
        return ResponseEntity.noContent().build();
    }

    // ---- exams
    @GetMapping("/exams")
    public PageResponse<ExamDto> exams(@RequestParam(required = false) Long subjectId,
                                       @RequestParam(required = false) String q,
                                       @RequestParam(defaultValue = "0") int page,
                                       @RequestParam(defaultValue = "20") int size) {
        return exams.list(subjectId, q, Math.max(page, 0), Math.max(size, 1));
    }

    @GetMapping("/exams/{id}")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ExamDto exam(@PathVariable Long id) {
        return exams.get(id);
    }

    @PostMapping("/exams")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ExamDto createExam(@Valid @RequestBody ExamRequest r) {
        return exams.create(r);
    }

    @PutMapping("/exams/{id}")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ExamDto updateExam(@PathVariable Long id, @Valid @RequestBody ExamRequest r) {
        return exams.update(id, r);
    }

    @DeleteMapping("/exams/{id}")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ResponseEntity<Void> deleteExam(@PathVariable Long id) {
        exams.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping(value = "/exams/{id}/question-paper", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ExamDto uploadPaper(@PathVariable Long id, @RequestParam("file") MultipartFile file) {
        return exams.uploadQuestionPaper(id, file);
    }

    @GetMapping("/exams/{id}/question-paper")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ResponseEntity<Resource> downloadPaper(@PathVariable Long id) {
        Path p = exams.questionPaper(id);
        return FileResponses.inline(p, exams.questionPaperName(id));
    }

    // ---- questions & blueprints
    @GetMapping("/exams/{examId}/questions")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public List<QuestionDto> questions(@PathVariable Long examId) {
        return questions.list(examId);
    }

    @PostMapping("/exams/{examId}/questions")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public QuestionDto addQuestion(@PathVariable Long examId, @Valid @RequestBody QuestionRequest r) {
        return questions.create(examId, r);
    }

    @PutMapping("/questions/{id}")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public QuestionDto updateQuestion(@PathVariable Long id, @Valid @RequestBody QuestionRequest r) {
        return questions.update(id, r);
    }

    @DeleteMapping("/questions/{id}")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public ResponseEntity<Void> deleteQuestion(@PathVariable Long id) {
        questions.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/questions/{id}/blueprint")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public BlueprintDto blueprint(@PathVariable Long id) {
        return questions.blueprint(id);
    }

    @PutMapping("/questions/{id}/blueprint")
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public BlueprintDto saveBlueprint(@PathVariable Long id, @Valid @RequestBody BlueprintRequest r) {
        return questions.saveBlueprint(id, r);
    }

    @PostMapping(value = "/questions/{id}/blueprint/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("hasAuthority('EXAM_MANAGE')")
    public BlueprintDto uploadBlueprint(@PathVariable Long id, @RequestParam("file") MultipartFile file) {
        return questions.uploadBlueprintFile(id, file);
    }

    // ---- students & dashboards
    @GetMapping("/students")
    @PreAuthorize("hasAnyRole('ADMIN','TEACHER')")
    public PageResponse<StudentDto> students(@RequestParam(required = false) String q,
                                             @RequestParam(defaultValue = "0") int page,
                                             @RequestParam(defaultValue = "20") int size) {
        return users.students(q, Math.max(page, 0), Math.max(size, 1));
    }

    @GetMapping("/teacher/stats")
    @PreAuthorize("hasRole('TEACHER')")
    public TeacherStatsDto teacherStats() {
        return evaluations.teacherStats();
    }

    @GetMapping("/student/performance")
    @PreAuthorize("hasRole('STUDENT')")
    public StudentPerformanceDto performance() {
        return evaluations.performance();
    }
}
