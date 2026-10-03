package com.inkgrade.report;

import com.inkgrade.domain.*;
import com.lowagie.text.*;
import com.lowagie.text.pdf.PdfContentByte;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.stream.Collectors;

@Service
public class PdfReportService {
    private static final Font H1 = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 20, new Color(40, 40, 120));
    private static final Font H2 = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 13);
    private static final Font B = FontFactory.getFont(FontFactory.HELVETICA, 10);
    private static final Font BB = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10);
    private static final Font SM = FontFactory.getFont(FontFactory.HELVETICA, 9, Color.DARK_GRAY);
    private static final DateTimeFormatter DF = DateTimeFormatter.ofPattern("dd MMM yyyy HH:mm 'UTC'").withZone(ZoneOffset.UTC);

    public byte[] build(Evaluation ev) {
        Submission sub = ev.getSubmission();
        Exam exam = sub.getExam();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Document doc = new Document(PageSize.A4, 40, 40, 40, 40);
        PdfWriter writer = PdfWriter.getInstance(doc, out);
        doc.open();

        doc.add(new Paragraph("InkGrade AI - Evaluation Report", H1));
        doc.add(new Paragraph(" "));
        PdfPTable info = new PdfPTable(2);
        info.setWidthPercentage(100);
        row(info, "Student", sub.getStudent().getUser().getFullName() + " (" + sub.getStudent().getRollNumber() + ")");
        row(info, "Subject", exam.getSubject().getName() + " (" + exam.getSubject().getCode() + ")");
        row(info, "Exam", exam.getTitle());
        row(info, "Status", ev.getStatus().name());
        double pct = ev.getMaxTotal() > 0 ? ev.getFinalTotal() / ev.getMaxTotal() * 100 : 0;
        row(info, "Total marks", fmt(ev.getFinalTotal()) + " / " + fmt(ev.getMaxTotal()) + String.format(Locale.ROOT, "  (%.1f%%)", pct));
        if (ev.getFinalizedAt() != null) row(info, "Finalized", DF.format(ev.getFinalizedAt()));
        doc.add(info);

        doc.add(new Paragraph(" "));
        doc.add(new Paragraph("Question-wise marks", H2));
        PdfPTable t = new PdfPTable(new float[]{1, 1.2f, 1.2f, 1.2f, 1.2f});
        t.setWidthPercentage(100);
        t.setSpacingBefore(6);
        for (String h : new String[]{"Q", "Max", "AI marks", "Final marks", "Confidence"}) header(t, h);
        for (QuestionEvaluation q : ev.getQuestionEvaluations()) {
            cell(t, "Q" + q.getQuestionNumber(), BB);
            cell(t, fmt(q.getMaxMarks()), B);
            cell(t, fmt(q.getAiMarks()), B);
            cell(t, fmt(q.effectiveMarks()), BB);
            cell(t, String.format(Locale.ROOT, "%.0f%%", q.getConfidence() * 100), B);
        }
        doc.add(t);

        doc.add(new Paragraph(" "));
        doc.add(new Paragraph("Performance chart", H2));
        float chartHeight = 18f * ev.getQuestionEvaluations().size() + 10;
        doc.add(new Paragraph(" "));
        float yTop = writer.getVerticalPosition(false);
        if (yTop - chartHeight < doc.bottomMargin()) {
            doc.newPage();
            yTop = writer.getVerticalPosition(false);
        }
        drawChart(writer.getDirectContent(), ev, doc.left(), yTop, doc.right() - doc.left());
        Paragraph spacer = new Paragraph(" ");
        spacer.setSpacingBefore(chartHeight);
        doc.add(spacer);

        for (QuestionEvaluation q : ev.getQuestionEvaluations()) {
            doc.add(new Paragraph(" "));
            doc.add(new Paragraph(String.format(Locale.ROOT, "Question %d  -  %s / %s", q.getQuestionNumber(),
                    fmt(q.effectiveMarks()), fmt(q.getMaxMarks())), H2));
            doc.add(new Paragraph(q.getQuestion().getText(), SM));
            if (!q.getMatchedConcepts().isEmpty()) {
                doc.add(new Paragraph("Matched concepts: " + String.join(", ", q.getMatchedConcepts()), B));
            }
            if (!q.getMissingConcepts().isEmpty()) {
                doc.add(new Paragraph("Missing concepts: " + String.join(", ", q.getMissingConcepts()),
                        FontFactory.getFont(FontFactory.HELVETICA, 10, new Color(170, 30, 30))));
            }
            if (!q.getMistakes().isEmpty()) {
                doc.add(new Paragraph("Detected mistakes:", BB));
                for (Mistake m : q.getMistakes()) {
                    String line = "- [" + m.getType() + "] " + m.getDescription()
                            + (m.getSuggestion() != null ? "  -> " + m.getSuggestion() : "");
                    doc.add(new Paragraph(line, B));
                }
            }
            String fb = q.getFeedbacks().stream().map(f -> (f.getSource() == Feedback.Source.TEACHER ? "Teacher: " : "AI: ") + f.getText())
                    .collect(Collectors.joining("\n"));
            if (!fb.isEmpty()) {
                doc.add(new Paragraph("Feedback:", BB));
                doc.add(new Paragraph(fb, B));
            }
        }
        doc.close();
        return out.toByteArray();
    }

    private void drawChart(PdfContentByte cb, Evaluation ev, float x, float yTop, float width) {
        float labelW = 40, barMax = width - labelW - 60, y = yTop - 14;
        for (QuestionEvaluation q : ev.getQuestionEvaluations()) {
            float ratio = q.getMaxMarks() > 0 ? (float) (q.effectiveMarks() / q.getMaxMarks()) : 0;
            cb.setColorFill(new Color(225, 228, 240));
            cb.rectangle(x + labelW, y, barMax, 11);
            cb.fill();
            cb.setColorFill(ratio >= 0.6 ? new Color(46, 160, 90) : ratio >= 0.35 ? new Color(230, 160, 30) : new Color(205, 60, 60));
            cb.rectangle(x + labelW, y, Math.max(0.5f, barMax * ratio), 11);
            cb.fill();
            cb.beginText();
            cb.setFontAndSize(FontFactory.getFont(FontFactory.HELVETICA).getBaseFont(), 9);
            cb.setColorFill(Color.BLACK);
            cb.setTextMatrix(x, y + 2);
            cb.showText("Q" + q.getQuestionNumber());
            cb.setTextMatrix(x + labelW + barMax + 6, y + 2);
            cb.showText(fmt(q.effectiveMarks()) + "/" + fmt(q.getMaxMarks()));
            cb.endText();
            y -= 18;
        }
    }

    private static void row(PdfPTable t, String k, String v) {
        PdfPCell a = new PdfPCell(new Phrase(k, BB));
        PdfPCell b = new PdfPCell(new Phrase(v, B));
        a.setBorder(Rectangle.NO_BORDER);
        b.setBorder(Rectangle.NO_BORDER);
        t.addCell(a);
        t.addCell(b);
    }

    private static void header(PdfPTable t, String s) {
        PdfPCell c = new PdfPCell(new Phrase(s, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE)));
        c.setBackgroundColor(new Color(60, 70, 140));
        c.setPadding(5);
        t.addCell(c);
    }

    private static void cell(PdfPTable t, String s, Font f) {
        PdfPCell c = new PdfPCell(new Phrase(s, f));
        c.setPadding(4);
        t.addCell(c);
    }

    private static String fmt(double d) {
        return d == Math.rint(d) ? String.valueOf((long) d) : String.format(Locale.ROOT, "%.1f", d);
    }
}
