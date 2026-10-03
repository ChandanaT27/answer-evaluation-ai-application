package com.inkgrade.service;

import com.inkgrade.domain.Subject;
import com.inkgrade.domain.User;
import com.inkgrade.dto.CatalogDtos.*;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.*;
import com.inkgrade.security.CurrentUser;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SubjectService {
    private final SubjectRepository subjects;
    private final ExamRepository exams;
    private final UserRepository users;
    private final AccessService access;
    private final Mapper mapper;
    private final AuditService audit;

    public SubjectService(SubjectRepository subjects, ExamRepository exams, UserRepository users,
                          AccessService access, Mapper mapper, AuditService audit) {
        this.subjects = subjects;
        this.exams = exams;
        this.users = users;
        this.access = access;
        this.mapper = mapper;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public PageResponse<SubjectDto> list(String q, boolean activeOnly, int page, int size) {
        Pageable p = PageRequest.of(page, Math.min(size, 200), Sort.by("name"));
        if (CurrentUser.isStudent()) {
            // students only see subjects in which they have published results
            Long sid = access.currentStudent().getId();
            String needle = UserService.norm(q).toLowerCase();
            List<Subject> list = exams.findPublishedForStudent(sid, null).stream().map(e -> e.getSubject()).distinct()
                    .filter(s -> needle.isEmpty() || s.getName().toLowerCase().contains(needle)).toList();
            Page<Subject> pg = new PageImpl<>(list, p, list.size());
            return PageResponse.of(pg, s -> mapper.subject(s, 0));
        }
        return PageResponse.of(subjects.search(UserService.norm(q), activeOnly, p),
                s -> mapper.subject(s, exams.countBySubjectId(s.getId())));
    }

    @Transactional
    public SubjectDto create(SubjectRequest r) {
        if (subjects.existsByCodeIgnoreCase(r.code())) throw ApiException.conflict("Subject code already exists");
        Subject s = new Subject();
        apply(s, r);
        User u = users.findById(CurrentUser.get().getId()).orElseThrow();
        s.setCreatedBy(u);
        subjects.save(s);
        audit.log("SUBJECT_CREATED", "Subject", s.getId(), s.getCode());
        return mapper.subject(s, 0);
    }

    @Transactional
    public SubjectDto update(Long id, SubjectRequest r) {
        Subject s = find(id);
        assertCanModify(s);
        if (!s.getCode().equalsIgnoreCase(r.code()) && subjects.existsByCodeIgnoreCase(r.code())) {
            throw ApiException.conflict("Subject code already exists");
        }
        apply(s, r);
        audit.log("SUBJECT_UPDATED", "Subject", id, s.getCode());
        return mapper.subject(s, exams.countBySubjectId(id));
    }

    @Transactional
    public void delete(Long id) {
        Subject s = find(id);
        assertCanModify(s);
        if (exams.countBySubjectId(id) > 0) {
            throw ApiException.conflict("Subject has exams; deactivate it instead of deleting");
        }
        subjects.delete(s);
        audit.log("SUBJECT_DELETED", "Subject", id, s.getCode());
    }

    private void assertCanModify(Subject s) {
        if (CurrentUser.isAdmin()) return;
        if (s.getCreatedBy() != null && s.getCreatedBy().getId().equals(CurrentUser.get().getId())) return;
        throw ApiException.forbidden("Only the creator or an administrator can modify this subject");
    }

    private void apply(Subject s, SubjectRequest r) {
        s.setName(r.name().trim());
        s.setCode(r.code().trim().toUpperCase());
        s.setDescription(r.description());
        if (r.active() != null) s.setActive(r.active());
    }

    Subject find(Long id) {
        return subjects.findById(id).orElseThrow(() -> ApiException.notFound("Subject"));
    }
}
