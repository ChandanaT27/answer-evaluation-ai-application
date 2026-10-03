package com.inkgrade.service;

import com.inkgrade.domain.Evaluation;
import com.inkgrade.report.PdfReportService;
import com.inkgrade.security.CurrentUser;
import com.inkgrade.exception.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ReportService {
    private final EvaluationService evaluations;
    private final AccessService access;
    private final PdfReportService pdf;
    private final AuditService audit;

    public ReportService(EvaluationService evaluations, AccessService access, PdfReportService pdf, AuditService audit) {
        this.evaluations = evaluations;
        this.access = access;
        this.pdf = pdf;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public byte[] report(Long evaluationId) {
        Evaluation ev = evaluations.find(evaluationId);
        access.assertEvaluationView(ev);
        if (!CurrentUser.isStudent() && !CurrentUser.get().getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals("REPORT_DOWNLOAD"))) {
            throw ApiException.forbidden("Report download not permitted");
        }
        byte[] bytes = pdf.build(ev);
        audit.log("REPORT_DOWNLOADED", "Evaluation", evaluationId, null);
        return bytes;
    }
}
