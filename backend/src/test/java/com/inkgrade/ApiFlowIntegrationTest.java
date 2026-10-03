package com.inkgrade;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inkgrade.ai.AiClient;
import com.inkgrade.ai.AiDtos;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ApiFlowIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper om;
    @MockBean AiClient ai;

    private String token(String user, String pass) throws Exception {
        MvcResult r = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content(om.writeValueAsString(java.util.Map.of("username", user, "password", pass))))
                .andExpect(status().isOk()).andReturn();
        return om.readTree(r.getResponse().getContentAsString()).get("token").asText();
    }

    private JsonNode json(MvcResult r) throws Exception {
        return om.readTree(r.getResponse().getContentAsString());
    }

    private MockHttpServletRequestBuilder auth(MockHttpServletRequestBuilder b, String token) {
        return b.header("Authorization", "Bearer " + token);
    }

    private JsonNode send(MockHttpServletRequestBuilder b, String token, Object body, int expected) throws Exception {
        b = auth(b, token);
        if (body != null) b.contentType(MediaType.APPLICATION_JSON).content(om.writeValueAsString(body));
        MvcResult r = mvc.perform(b).andExpect(status().is(expected)).andReturn();
        String c = r.getResponse().getContentAsString();
        return c.isEmpty() || c.startsWith("%PDF") ? null : om.readTree(c);
    }

    @Test
    void authAndRoleEnforcement() throws Exception {
        mvc.perform(get("/api/exams")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"username\":\"admin\",\"password\":\"wrong\"}")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());

        String admin = token("admin", "Admin@123");
        String suffix = UUID.randomUUID().toString().substring(0, 6);
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "stu" + suffix, "email", "s" + suffix + "@x.io",
                "fullName", "S", "password", "Password1", "role", "STUDENT", "rollNumber", "RR" + suffix), 201);
        String student = token("stu" + suffix, "Password1");
        send(get("/api/admin/users"), student, null, 403);
        send(post("/api/subjects"), student, java.util.Map.of("name", "X", "code", "X1"), 403);
        // duplicate username and validation
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "stu" + suffix, "email", "o" + suffix + "@x.io",
                "fullName", "S", "password", "Password1", "role", "STUDENT", "rollNumber", "Z" + suffix), 409);
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "ab", "email", "bad", "fullName", "",
                "password", "x", "role", "STUDENT"), 400);
    }

    @Test
    void fullEvaluationFlowWithStudentIsolation() throws Exception {
        when(ai.ocr(any(), any())).thenReturn(new AiDtos.OcrResult("Q1. answer one\nQ2. answer two", 0.9, 1, "mock"));
        when(ai.evaluate(any())).thenAnswer(inv -> {
            AiDtos.EvaluateRequest req = inv.getArgument(0);
            List<AiDtos.QuestionResult> res = req.questions().stream().map(q -> new AiDtos.QuestionResult(q.id(),
                    q.number(), "answer " + q.number() + " proces", true, q.maxMarks(), q.maxMarks() / 2, 0.5, 0.5,
                    List.of("alpha"), List.of("beta"),
                    List.of(new AiDtos.MistakeOut("SPELLING", "Possible spelling error: 'proces'", "proces", 9, 15, "process"),
                            new AiDtos.MistakeOut("MISSING_CONCEPT", "Missing concept: beta", null, null, null, null)),
                    "Partially correct.", 0.8)).toList();
            return new AiDtos.EvaluateResponse(res, "mock");
        });

        String admin = token("admin", "Admin@123");
        String sx = UUID.randomUUID().toString().substring(0, 6);
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "t" + sx, "email", "t" + sx + "@x.io",
                "fullName", "Teach", "password", "Password1", "role", "TEACHER", "employeeId", "E" + sx), 201);
        long s1 = send(post("/api/admin/users"), admin, java.util.Map.of("username", "a" + sx, "email", "a" + sx + "@x.io",
                "fullName", "Alice", "password", "Password1", "role", "STUDENT", "rollNumber", "A" + sx), 201).get("id").asLong();
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "b" + sx, "email", "b" + sx + "@x.io",
                "fullName", "Bob", "password", "Password1", "role", "STUDENT", "rollNumber", "B" + sx), 201);

        String teacher = token("t" + sx, "Password1");
        String alice = token("a" + sx, "Password1");
        String bob = token("b" + sx, "Password1");

        JsonNode students = send(get("/api/students?q=Alice"), teacher, null, 200);
        long studentId = students.get("content").get(0).get("id").asLong();

        long subjectId = send(post("/api/subjects"), teacher, java.util.Map.of("name", "Biology " + sx, "code", "BIO" + sx), 201).get("id").asLong();
        long examId = send(post("/api/exams"), teacher, java.util.Map.of("title", "Midterm", "subjectId", subjectId), 201).get("id").asLong();
        send(post("/api/exams"), alice, java.util.Map.of("title", "Hack", "subjectId", subjectId), 403);

        long q1 = send(post("/api/exams/" + examId + "/questions"), teacher, java.util.Map.of("text", "Explain A", "maxMarks", 5), 201).get("id").asLong();
        long q2 = send(post("/api/exams/" + examId + "/questions"), teacher, java.util.Map.of("text", "Explain B", "maxMarks", 3.5), 201).get("id").asLong();
        send(post("/api/exams/" + examId + "/questions"), teacher, java.util.Map.of("text", "x", "maxMarks", -1), 400);

        // Cannot evaluate before blueprints exist
        mvc.perform(multipart("/api/exams/" + examId + "/submissions").file(new MockMultipartFile("file", "sheet.txt", "text/plain", "Q1. answer one".getBytes()))
                .param("studentId", String.valueOf(studentId)).header("Authorization", "Bearer " + teacher)).andExpect(status().isCreated());
        long subId = send(get("/api/exams/" + examId + "/submissions"), teacher, null, 200).get(0).get("id").asLong();
        send(post("/api/submissions/" + subId + "/evaluate"), teacher, null, 400);

        for (long q : new long[]{q1, q2}) {
            send(put("/api/questions/" + q + "/blueprint"), teacher, java.util.Map.of("modelAnswer", "Model answer text",
                    "concepts", List.of(java.util.Map.of("name", "alpha", "keywords", List.of("a1"), "weight", 1),
                            java.util.Map.of("name", "beta", "keywords", List.of(), "weight", 2))), 200);
        }
        send(post("/api/submissions/" + subId + "/evaluate"), teacher, null, 202);

        long evalId = -1;
        for (int i = 0; i < 50 && evalId < 0; i++) {
            JsonNode s = send(get("/api/submissions/" + subId), teacher, null, 200);
            if ("FAILED".equals(s.get("status").asText())) fail("evaluation failed: " + s);
            if (!s.get("evaluationId").isNull()) evalId = s.get("evaluationId").asLong();
            else Thread.sleep(100);
        }
        assertTrue(evalId > 0, "evaluation should complete");

        JsonNode detail = send(get("/api/evaluations/" + evalId), teacher, null, 200);
        assertEquals(8.5, detail.get("summary").get("maxTotal").asDouble());
        assertEquals(4.25, detail.get("summary").get("aiTotal").asDouble());
        JsonNode qe1 = detail.get("questions").get(0);
        assertEquals(2.5, qe1.get("aiMarks").asDouble());
        assertTrue(qe1.get("finalMarks").isNull());
        assertEquals("beta", qe1.get("missingConcepts").get(0).asText());
        assertEquals(1, qe1.get("mistakes").size());

        // student cannot see unpublished result
        send(get("/api/evaluations/" + evalId), alice, null, 403);
        assertEquals(0, send(get("/api/evaluations"), alice, null, 200).get("content").size());

        // teacher override: bounds + valid
        long qeId = qe1.get("id").asLong();
        send(put("/api/evaluations/" + evalId + "/questions/" + qeId), teacher, java.util.Map.of("finalMarks", 6), 400);
        JsonNode upd = send(put("/api/evaluations/" + evalId + "/questions/" + qeId), teacher,
                java.util.Map.of("finalMarks", 4, "comment", "Good attempt"), 200);
        assertEquals(5.75, upd.get("summary").get("finalTotal").asDouble());
        assertEquals("UNDER_REVIEW", upd.get("summary").get("status").asText());
        assertEquals(2.5, upd.get("questions").get(0).get("aiMarks").asDouble()); // AI marks preserved

        send(post("/api/evaluations/" + evalId + "/finalize"), teacher, null, 200);

        // student sees only own, bob sees nothing
        JsonNode own = send(get("/api/evaluations/" + evalId), alice, null, 200);
        assertEquals("FINALIZED", own.get("summary").get("status").asText());
        send(get("/api/evaluations/" + evalId), bob, null, 403);
        send(get("/api/evaluations/" + evalId + "/report"), bob, null, 403);
        send(get("/api/evaluations/" + evalId + "/history"), alice, null, 403);
        send(delete("/api/evaluations/" + evalId), alice, null, 403);
        assertEquals(1, send(get("/api/evaluations"), alice, null, 200).get("content").size());
        assertEquals(0, send(get("/api/evaluations"), bob, null, 200).get("content").size());
        assertEquals(1, send(get("/api/exams"), alice, null, 200).get("content").size());
        assertEquals(1, send(get("/api/student/performance"), alice, null, 200).get("exams").size());
        mvc.perform(get("/api/submissions/" + subId + "/file").header("Authorization", "Bearer " + bob)).andExpect(status().isForbidden());
        mvc.perform(get("/api/submissions/" + subId + "/file").header("Authorization", "Bearer " + alice)).andExpect(status().isOk());

        // another teacher cannot touch it
        String sy = UUID.randomUUID().toString().substring(0, 6);
        send(post("/api/admin/users"), admin, java.util.Map.of("username", "t" + sy, "email", "t" + sy + "@x.io",
                "fullName", "Other", "password", "Password1", "role", "TEACHER"), 201);
        String other = token("t" + sy, "Password1");
        send(get("/api/evaluations/" + evalId), other, null, 403);
        send(put("/api/evaluations/" + evalId + "/questions/" + qeId), other, java.util.Map.of("finalMarks", 1), 403);

        // PDF report
        MvcResult pdf = mvc.perform(get("/api/evaluations/" + evalId + "/report").header("Authorization", "Bearer " + alice))
                .andExpect(status().isOk()).andReturn();
        assertTrue(new String(pdf.getResponse().getContentAsByteArray(), 0, 4).startsWith("%PDF"));

        // filters
        assertEquals(1, send(get("/api/evaluations?q=Alice&status=FINALIZED&examId=" + examId), teacher, null, 200).get("content").size());
        assertEquals(0, send(get("/api/evaluations?q=nobody"), teacher, null, 200).get("content").size());
        assertTrue(send(get("/api/evaluations/" + evalId + "/history"), teacher, null, 200).size() >= 3);

        // permission management: revoke delete from teacher role
        JsonNode roles = send(get("/api/admin/roles"), admin, null, 200);
        long teacherRole = 0;
        for (JsonNode r : roles) if ("TEACHER".equals(r.get("name").asText())) teacherRole = r.get("id").asLong();
        send(put("/api/admin/roles/" + teacherRole + "/permissions"), admin, java.util.Map.of("permissions",
                List.of("EXAM_MANAGE", "SUBJECT_MANAGE", "SUBMISSION_UPLOAD", "EVALUATION_RUN", "EVALUATION_REVIEW", "REPORT_DOWNLOAD")), 200);
        send(delete("/api/evaluations/" + evalId), teacher, null, 403);
        send(put("/api/admin/roles/" + teacherRole + "/permissions"), admin, java.util.Map.of("permissions",
                List.of("EXAM_MANAGE", "SUBJECT_MANAGE", "SUBMISSION_UPLOAD", "EVALUATION_RUN", "EVALUATION_REVIEW", "EVALUATION_DELETE", "REPORT_DOWNLOAD")), 200);
        send(delete("/api/evaluations/" + evalId), teacher, null, 204);
        send(get("/api/evaluations/" + evalId), teacher, null, 404);

        JsonNode audit = send(get("/api/admin/audit-logs?q=EVALUATION"), admin, null, 200);
        assertTrue(audit.get("totalElements").asLong() >= 3);
        assertTrue(send(get("/api/admin/stats"), admin, null, 200).get("students").asLong() >= 2);
        assertNotNull(s1);
    }
}
