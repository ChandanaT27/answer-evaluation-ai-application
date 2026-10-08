from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..errors import ApiException
from ..models import Evaluation, Permission
from ..security import Principal
from . import access, audit
from .evaluations import find

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, textColor=colors.Color(40 / 255, 40 / 255, 120 / 255),
                    leading=26)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, spaceBefore=10)
B = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13)
BB = ParagraphStyle("bb", parent=B, fontName="Helvetica-Bold")
SM = ParagraphStyle("sm", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.darkgrey)
RED = ParagraphStyle("red", parent=B, textColor=colors.Color(170 / 255, 30 / 255, 30 / 255))


def fmt(d: float) -> str:
    return str(int(d)) if d == int(d) else f"{d:.1f}"


def _p(text, style=B) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


class BarChart(Flowable):
    def __init__(self, ev: Evaluation, width: float):
        super().__init__()
        self.qs = ev.question_evaluations
        self.width = width
        self.height = 18 * len(self.qs) + 10

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        label_w, bar_max = 40, self.width - 40 - 60
        y = self.height - 14
        for q in self.qs:
            ratio = q.effective_marks() / q.max_marks if q.max_marks > 0 else 0
            c.setFillColorRGB(225 / 255, 228 / 255, 240 / 255)
            c.rect(label_w, y, bar_max, 11, stroke=0, fill=1)
            if ratio >= 0.6:
                c.setFillColorRGB(46 / 255, 160 / 255, 90 / 255)
            elif ratio >= 0.35:
                c.setFillColorRGB(230 / 255, 160 / 255, 30 / 255)
            else:
                c.setFillColorRGB(205 / 255, 60 / 255, 60 / 255)
            c.rect(label_w, y, max(0.5, bar_max * ratio), 11, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9)
            c.drawString(0, y + 2, f"Q{q.question_number}")
            c.drawString(label_w + bar_max + 6, y + 2, f"{fmt(q.effective_marks())}/{fmt(q.max_marks)}")
            y -= 18


def build(ev: Evaluation) -> bytes:
    sub = ev.submission
    exam = sub.exam
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40,
                            title="InkGrade AI - Evaluation Report")
    width = A4[0] - 80
    story = [_p("InkGrade AI - Evaluation Report", H1), Spacer(1, 12)]

    pct = ev.final_total / ev.max_total * 100 if ev.max_total > 0 else 0
    rows = [("Student", f"{sub.student.user.full_name} ({sub.student.roll_number})"),
            ("Subject", f"{exam.subject.name} ({exam.subject.code})"),
            ("Exam", exam.title), ("Status", ev.status),
            ("Total marks", f"{fmt(ev.final_total)} / {fmt(ev.max_total)}  ({pct:.1f}%)")]
    if ev.finalized_at is not None:
        rows.append(("Finalized", ev.finalized_at.strftime("%d %b %Y %H:%M UTC")))
    info = Table([[_p(k, BB), _p(v)] for k, v in rows], colWidths=[width * 0.3, width * 0.7])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [info, Spacer(1, 12), _p("Question-wise marks", H2), Spacer(1, 6)]

    data = [[_p(h, ParagraphStyle("th", parent=BB, textColor=colors.white))
             for h in ("Q", "Max", "AI marks", "Final marks", "Confidence")]]
    for q in ev.question_evaluations:
        data.append([_p(f"Q{q.question_number}", BB), _p(fmt(q.max_marks)), _p(fmt(q.ai_marks)),
                     _p(fmt(q.effective_marks()), BB), _p(f"{q.confidence * 100:.0f}%")])
    t = Table(data, colWidths=[width * w for w in (0.16, 0.21, 0.21, 0.21, 0.21)])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.Color(60 / 255, 70 / 255, 140 / 255)),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 12), _p("Performance chart", H2), Spacer(1, 6), BarChart(ev, width)]

    for q in ev.question_evaluations:
        story += [Spacer(1, 8),
                  _p(f"Question {q.question_number}  -  {fmt(q.effective_marks())} / {fmt(q.max_marks)}", H2),
                  _p(q.question.text, SM)]
        if q.matched_concepts:
            story.append(_p("Matched concepts: " + ", ".join(q.matched_concepts)))
        if q.missing_concepts:
            story.append(_p("Missing concepts: " + ", ".join(q.missing_concepts), RED))
        if q.mistakes:
            story.append(_p("Detected mistakes:", BB))
            for m in q.mistakes:
                story.append(_p(f"- [{m.type}] {m.description}" + (f"  -> {m.suggestion}" if m.suggestion else "")))
        if q.feedbacks:
            story.append(_p("Feedback:", BB))
            story.append(_p("\n".join(("Teacher: " if f.source == "TEACHER" else "AI: ") + f.text
                                      for f in q.feedbacks)))
    doc.build(story)
    return buf.getvalue()


def report(db: Session, user: Principal, evaluation_id: int) -> bytes:
    ev = find(db, evaluation_id)
    access.assert_evaluation_view(user, ev)
    if not user.is_student and not user.has(Permission.REPORT_DOWNLOAD):
        raise ApiException.forbidden("Report download not permitted")
    data = build(ev)
    audit.log(db, user, "REPORT_DOWNLOADED", "Evaluation", evaluation_id, None)
    db.commit()
    return data
