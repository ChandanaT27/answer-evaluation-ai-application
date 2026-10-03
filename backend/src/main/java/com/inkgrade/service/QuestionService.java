package com.inkgrade.service;

import com.inkgrade.ai.AiClient;
import com.inkgrade.ai.AiDtos;
import com.inkgrade.domain.*;
import com.inkgrade.dto.CatalogDtos.*;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.BlueprintRepository;
import com.inkgrade.repository.QuestionRepository;
import com.inkgrade.storage.FileStorageService;
import com.inkgrade.storage.StoredFile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.util.List;

@Service
public class QuestionService {
    private final QuestionRepository questions;
    private final BlueprintRepository blueprints;
    private final ExamService examService;
    private final AccessService access;
    private final FileStorageService storage;
    private final AiClient ai;
    private final Mapper mapper;
    private final AuditService audit;

    public QuestionService(QuestionRepository questions, BlueprintRepository blueprints, ExamService examService,
                           AccessService access, FileStorageService storage,
                           AiClient ai, Mapper mapper, AuditService audit) {
        this.questions = questions;
        this.blueprints = blueprints;
        this.examService = examService;
        this.access = access;
        this.storage = storage;
        this.ai = ai;
        this.mapper = mapper;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public List<QuestionDto> list(Long examId) {
        access.assertExamManage(examService.find(examId));
        return questions.findByExamIdOrderByNumberAsc(examId).stream()
                .map(q -> mapper.question(q, blueprints.findByQuestionId(q.getId()).isPresent())).toList();
    }

    @Transactional
    public QuestionDto create(Long examId, QuestionRequest r) {
        Exam exam = examService.find(examId);
        access.assertExamManage(exam);
        int number = r.number() != null ? r.number()
                : questions.findByExamIdOrderByNumberAsc(examId).stream().mapToInt(Question::getNumber).max().orElse(0) + 1;
        if (questions.existsByExamIdAndNumber(examId, number)) {
            throw ApiException.conflict("Question " + number + " already exists in this exam");
        }
        Question q = new Question();
        q.setExam(exam);
        q.setNumber(number);
        q.setText(r.text().trim());
        q.setMaxMarks(r.maxMarks());
        questions.save(q);
        audit.log("QUESTION_CREATED", "Question", q.getId(), "Exam " + examId + " Q" + number);
        return mapper.question(q, false);
    }

    @Transactional
    public QuestionDto update(Long id, QuestionRequest r) {
        Question q = find(id);
        access.assertExamManage(q.getExam());
        if (r.number() != null && r.number() != q.getNumber()) {
            if (questions.existsByExamIdAndNumber(q.getExam().getId(), r.number())) {
                throw ApiException.conflict("Question " + r.number() + " already exists in this exam");
            }
            q.setNumber(r.number());
        }
        q.setText(r.text().trim());
        q.setMaxMarks(r.maxMarks());
        audit.log("QUESTION_UPDATED", "Question", id, null);
        return mapper.question(q, blueprints.findByQuestionId(id).isPresent());
    }

    @Transactional
    public void delete(Long id) {
        Question q = find(id);
        access.assertExamManage(q.getExam());
        blueprints.findByQuestionId(id).ifPresent(blueprints::delete);
        questions.delete(q);
        questions.flush();
        audit.log("QUESTION_DELETED", "Question", id, null);
    }

    @Transactional(readOnly = true)
    public BlueprintDto blueprint(Long questionId) {
        Question q = find(questionId);
        access.assertExamManage(q.getExam());
        return blueprints.findByQuestionId(questionId).map(mapper::blueprint)
                .orElse(new BlueprintDto(questionId, "", null, List.of()));
    }

    @Transactional
    public BlueprintDto saveBlueprint(Long questionId, BlueprintRequest r) {
        Question q = find(questionId);
        access.assertExamManage(q.getExam());
        boolean hasText = r.modelAnswer() != null && !r.modelAnswer().isBlank();
        boolean hasConcepts = r.concepts() != null && !r.concepts().isEmpty();
        if (!hasText && !hasConcepts) {
            throw ApiException.badRequest("Provide a model answer and/or at least one concept");
        }
        Blueprint b = blueprints.findByQuestionId(questionId).orElseGet(() -> {
            Blueprint nb = new Blueprint();
            nb.setQuestion(q);
            return nb;
        });
        b.setModelAnswer(r.modelAnswer() == null ? "" : r.modelAnswer().trim());
        b.getConcepts().clear();
        if (hasConcepts) {
            for (ConceptDto c : r.concepts()) {
                BlueprintConcept bc = new BlueprintConcept();
                bc.setBlueprint(b);
                bc.setName(c.name().trim());
                bc.setKeywords(c.keywords() == null ? "" : String.join(",", c.keywords().stream()
                        .map(String::trim).filter(s -> !s.isEmpty()).map(s -> s.replace(",", " ")).toList()));
                bc.setWeight(c.weight() == null ? 1.0 : c.weight());
                b.getConcepts().add(bc);
            }
        }
        blueprints.save(b);
        audit.log("BLUEPRINT_SAVED", "Question", questionId, null);
        return mapper.blueprint(b);
    }

    /** Uploads a model-answer file (PDF/image/text), runs OCR, and stores the text as the model answer. */
    @Transactional
    public BlueprintDto uploadBlueprintFile(Long questionId, MultipartFile file) {
        Question q = find(questionId);
        access.assertExamManage(q.getExam());
        StoredFile f = storage.store(file, "blueprints");
        Path path = storage.resolve(f.relativePath());
        AiDtos.OcrResult ocr;
        try {
            ocr = ai.ocr(path, f.originalName());
        } finally {
            storage.deleteQuietly(f.relativePath());
        }
        if (ocr.text() == null || ocr.text().isBlank()) {
            throw ApiException.badRequest("No text could be extracted from the uploaded file");
        }
        Blueprint b = blueprints.findByQuestionId(questionId).orElseGet(() -> {
            Blueprint nb = new Blueprint();
            nb.setQuestion(q);
            return nb;
        });
        b.setModelAnswer(ocr.text().trim());
        b.setSourceFileName(f.originalName());
        blueprints.save(b);
        audit.log("BLUEPRINT_UPLOADED", "Question", questionId, f.originalName());
        return mapper.blueprint(b);
    }

    Question find(Long id) {
        return questions.findById(id).orElseThrow(() -> ApiException.notFound("Question"));
    }
}
