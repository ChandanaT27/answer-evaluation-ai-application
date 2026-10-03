package com.inkgrade.web;

import com.inkgrade.domain.EvaluationStatus;
import com.inkgrade.dto.EvaluationDtos.*;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.service.*;
import jakarta.validation.Valid;
import org.springframework.core.io.Resource;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api")
public class EvaluationController {
    private final SubmissionService submissions;
    private final EvaluationService evaluations;
    private final ReportService reports;

    public EvaluationController(SubmissionService submissions, EvaluationService evaluations, ReportService reports) {
        this.submissions = submissions;
        this.evaluations = evaluations;
        this.reports = reports;
    }

    // ---- submissions
    @GetMapping("/exams/{examId}/submissions")
    @PreAuthorize("hasAuthority('SUBMISSION_UPLOAD')")
    public List<SubmissionDto> submissions(@PathVariable Long examId) {
        return submissions.list(examId);
    }

    @PostMapping(value = "/exams/{examId}/submissions", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAuthority('SUBMISSION_UPLOAD')")
    public SubmissionDto upload(@PathVariable Long examId, @RequestParam Long studentId,
                                @RequestParam("file") MultipartFile file) {
        return submissions.upload(examId, studentId, file);
    }

    @GetMapping("/submissions/{id}")
    @PreAuthorize("hasAuthority('SUBMISSION_UPLOAD')")
    public SubmissionDto submission(@PathVariable Long id) {
        return submissions.get(id);
    }

    @DeleteMapping("/submissions/{id}")
    @PreAuthorize("hasAuthority('SUBMISSION_UPLOAD')")
    public ResponseEntity<Void> deleteSubmission(@PathVariable Long id) {
        submissions.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/submissions/{id}/file")
    public ResponseEntity<Resource> file(@PathVariable Long id) {
        var f = submissions.file(id);
        return FileResponses.inline(f.path(), f.name());
    }

    @PostMapping("/submissions/{id}/evaluate")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @PreAuthorize("hasAuthority('EVALUATION_RUN')")
    public SubmissionDto evaluate(@PathVariable Long id) {
        return evaluations.start(id);
    }

    // ---- evaluations
    @GetMapping("/evaluations")
    public PageResponse<EvaluationSummaryDto> search(
            @RequestParam(required = false) Long examId, @RequestParam(required = false) Long subjectId,
            @RequestParam(required = false) Long studentId, @RequestParam(required = false) EvaluationStatus status,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(required = false) String q, @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return evaluations.search(examId, subjectId, studentId, status, from, to, q, Math.max(page, 0), Math.max(size, 1));
    }

    @GetMapping("/evaluations/{id}")
    public EvaluationDetailDto get(@PathVariable Long id) {
        return evaluations.get(id);
    }

    @PutMapping("/evaluations/{id}/questions/{qeId}")
    @PreAuthorize("hasAuthority('EVALUATION_REVIEW')")
    public EvaluationDetailDto review(@PathVariable Long id, @PathVariable Long qeId,
                                      @Valid @RequestBody ReviewRequest r) {
        return evaluations.review(id, qeId, r);
    }

    @PostMapping("/evaluations/{id}/finalize")
    @PreAuthorize("hasAuthority('EVALUATION_REVIEW')")
    public EvaluationDetailDto finalizeEval(@PathVariable Long id) {
        return evaluations.finalizeEvaluation(id);
    }

    @PostMapping("/evaluations/{id}/reopen")
    @PreAuthorize("hasAuthority('EVALUATION_REVIEW')")
    public EvaluationDetailDto reopen(@PathVariable Long id) {
        return evaluations.reopen(id);
    }

    @DeleteMapping("/evaluations/{id}")
    @PreAuthorize("hasAuthority('EVALUATION_DELETE')")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        evaluations.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/evaluations/{id}/history")
    @PreAuthorize("hasAnyRole('ADMIN','TEACHER')")
    public List<HistoryDto> history(@PathVariable Long id) {
        return evaluations.history(id);
    }

    @GetMapping("/evaluations/{id}/report")
    public ResponseEntity<byte[]> report(@PathVariable Long id) {
        byte[] pdf = reports.report(id);
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename("inkgrade-report-" + id + ".pdf").build().toString())
                .body(pdf);
    }
}
