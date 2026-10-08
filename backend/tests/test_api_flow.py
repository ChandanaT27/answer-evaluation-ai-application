import time
import uuid


def login(c, user, pw):
    r = c.post("/api/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def call(c, method, url, h, expected, **kw):
    r = c.request(method, url, headers=h, **kw)
    assert r.status_code == expected, f"{method} {url}: {r.status_code} {r.text}"
    return r


def uid():
    return uuid.uuid4().hex[:6]


def make_user(c, admin, **body):
    base = {"password": "Password1"}
    base.update(body)
    return call(c, "POST", "/api/admin/users", admin, 201, json=base).json()


def test_auth_and_role_enforcement(client):
    c = client
    assert c.get("/api/exams").status_code == 401
    assert c.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={}).status_code == 400
    assert c.get("/actuator/health").json() == {"status": "UP"}

    admin = login(c, "admin", "Admin@123")
    s = uid()
    make_user(c, admin, username="stu" + s, email=f"s{s}@x.io", fullName="S", role="STUDENT", rollNumber="RR" + s)
    student = login(c, "stu" + s, "Password1")
    call(c, "GET", "/api/admin/users", student, 403)
    call(c, "POST", "/api/subjects", student, 403, json={"name": "X", "code": "X1"})
    call(c, "POST", "/api/admin/users", admin, 409, json={
        "username": "stu" + s, "email": f"o{s}@x.io", "fullName": "S", "password": "Password1",
        "role": "STUDENT", "rollNumber": "Z" + s})
    call(c, "POST", "/api/admin/users", admin, 400, json={
        "username": "ab", "email": "bad", "fullName": "", "password": "x", "role": "STUDENT"})


def test_full_evaluation_flow_with_student_isolation(client):
    c = client
    admin = login(c, "admin", "Admin@123")
    sx = uid()
    make_user(c, admin, username="t" + sx, email=f"t{sx}@x.io", fullName="Teach", role="TEACHER", employeeId="E" + sx)
    make_user(c, admin, username="a" + sx, email=f"a{sx}@x.io", fullName="Alice", role="STUDENT", rollNumber="A" + sx)
    make_user(c, admin, username="b" + sx, email=f"b{sx}@x.io", fullName="Bob", role="STUDENT", rollNumber="B" + sx)
    teacher, alice, bob = login(c, "t" + sx, "Password1"), login(c, "a" + sx, "Password1"), login(c, "b" + sx, "Password1")

    student_id = call(c, "GET", "/api/students?q=Alice", teacher, 200).json()["content"][0]["id"]
    subject_id = call(c, "POST", "/api/subjects", teacher, 201, json={"name": "Biology " + sx, "code": "BIO" + sx}).json()["id"]
    exam_id = call(c, "POST", "/api/exams", teacher, 201, json={"title": "Midterm", "subjectId": subject_id}).json()["id"]
    call(c, "POST", "/api/exams", alice, 403, json={"title": "Hack", "subjectId": subject_id})
    q1 = call(c, "POST", f"/api/exams/{exam_id}/questions", teacher, 201, json={"text": "Explain A", "maxMarks": 5}).json()["id"]
    q2 = call(c, "POST", f"/api/exams/{exam_id}/questions", teacher, 201, json={"text": "Explain B", "maxMarks": 3.5}).json()["id"]
    call(c, "POST", f"/api/exams/{exam_id}/questions", teacher, 400, json={"text": "x", "maxMarks": -1})

    call(c, "POST", f"/api/exams/{exam_id}/submissions", teacher, 201, data={"studentId": str(student_id)},
         files={"file": ("sheet.txt", b"Q1. answer one", "text/plain")})
    sub_id = call(c, "GET", f"/api/exams/{exam_id}/submissions", teacher, 200).json()[0]["id"]
    call(c, "POST", f"/api/submissions/{sub_id}/evaluate", teacher, 400)  # no blueprints yet

    for q in (q1, q2):
        call(c, "PUT", f"/api/questions/{q}/blueprint", teacher, 200, json={
            "modelAnswer": "Model answer text",
            "concepts": [{"name": "alpha", "keywords": ["a1"], "weight": 1}, {"name": "beta", "keywords": [], "weight": 2}]})
    call(c, "POST", f"/api/submissions/{sub_id}/evaluate", teacher, 202)

    eval_id = None
    for _ in range(100):
        s = call(c, "GET", f"/api/submissions/{sub_id}", teacher, 200).json()
        assert s["status"] != "FAILED", s
        if s["evaluationId"] is not None:
            eval_id = s["evaluationId"]
            break
        time.sleep(0.1)
    assert eval_id, "evaluation should complete"

    detail = call(c, "GET", f"/api/evaluations/{eval_id}", teacher, 200).json()
    assert detail["summary"]["maxTotal"] == 8.5
    assert detail["summary"]["aiTotal"] == 4.25
    qe1 = detail["questions"][0]
    assert qe1["aiMarks"] == 2.5 and qe1["finalMarks"] is None
    assert qe1["missingConcepts"] == ["beta"]
    assert len(qe1["mistakes"]) == 1

    call(c, "GET", f"/api/evaluations/{eval_id}", alice, 403)
    assert call(c, "GET", "/api/evaluations", alice, 200).json()["content"] == []

    qe_id = qe1["id"]
    call(c, "PUT", f"/api/evaluations/{eval_id}/questions/{qe_id}", teacher, 400, json={"finalMarks": 6})
    upd = call(c, "PUT", f"/api/evaluations/{eval_id}/questions/{qe_id}", teacher, 200,
               json={"finalMarks": 4, "comment": "Good attempt"}).json()
    assert upd["summary"]["finalTotal"] == 5.75
    assert upd["summary"]["status"] == "UNDER_REVIEW"
    assert upd["questions"][0]["aiMarks"] == 2.5

    call(c, "POST", f"/api/evaluations/{eval_id}/finalize", teacher, 200)

    own = call(c, "GET", f"/api/evaluations/{eval_id}", alice, 200).json()
    assert own["summary"]["status"] == "FINALIZED"
    call(c, "GET", f"/api/evaluations/{eval_id}", bob, 403)
    call(c, "GET", f"/api/evaluations/{eval_id}/report", bob, 403)
    call(c, "GET", f"/api/evaluations/{eval_id}/history", alice, 403)
    call(c, "DELETE", f"/api/evaluations/{eval_id}", alice, 403)
    assert len(call(c, "GET", "/api/evaluations", alice, 200).json()["content"]) == 1
    assert call(c, "GET", "/api/evaluations", bob, 200).json()["content"] == []
    assert len(call(c, "GET", "/api/exams", alice, 200).json()["content"]) == 1
    assert len(call(c, "GET", "/api/student/performance", alice, 200).json()["exams"]) == 1
    call(c, "GET", f"/api/submissions/{sub_id}/file", bob, 403)
    call(c, "GET", f"/api/submissions/{sub_id}/file", alice, 200)

    sy = uid()
    make_user(c, admin, username="t" + sy, email=f"t{sy}@x.io", fullName="Other", role="TEACHER")
    other = login(c, "t" + sy, "Password1")
    call(c, "GET", f"/api/evaluations/{eval_id}", other, 403)
    call(c, "PUT", f"/api/evaluations/{eval_id}/questions/{qe_id}", other, 403, json={"finalMarks": 1})

    pdf = call(c, "GET", f"/api/evaluations/{eval_id}/report", alice, 200)
    assert pdf.content.startswith(b"%PDF")
    assert "inkgrade-report" in pdf.headers["content-disposition"]

    assert len(call(c, "GET", f"/api/evaluations?q=Alice&status=FINALIZED&examId={exam_id}", teacher, 200).json()["content"]) == 1
    assert call(c, "GET", "/api/evaluations?q=nobody", teacher, 200).json()["content"] == []
    assert len(call(c, "GET", f"/api/evaluations/{eval_id}/history", teacher, 200).json()) >= 3

    roles = call(c, "GET", "/api/admin/roles", admin, 200).json()
    teacher_role = next(r["id"] for r in roles if r["name"] == "TEACHER")
    allp = ["EXAM_MANAGE", "SUBJECT_MANAGE", "SUBMISSION_UPLOAD", "EVALUATION_RUN", "EVALUATION_REVIEW",
            "EVALUATION_DELETE", "REPORT_DOWNLOAD"]
    call(c, "PUT", f"/api/admin/roles/{teacher_role}/permissions", admin, 200,
         json={"permissions": [p for p in allp if p != "EVALUATION_DELETE"]})
    call(c, "DELETE", f"/api/evaluations/{eval_id}", teacher, 403)
    call(c, "PUT", f"/api/admin/roles/{teacher_role}/permissions", admin, 200, json={"permissions": allp})
    call(c, "DELETE", f"/api/evaluations/{eval_id}", teacher, 204)
    call(c, "GET", f"/api/evaluations/{eval_id}", teacher, 404)

    audit = call(c, "GET", "/api/admin/audit-logs?q=EVALUATION", admin, 200).json()
    assert audit["totalElements"] >= 3
    assert call(c, "GET", "/api/admin/stats", admin, 200).json()["students"] >= 2
