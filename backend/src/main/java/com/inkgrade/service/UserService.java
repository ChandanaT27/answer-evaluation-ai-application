package com.inkgrade.service;

import com.inkgrade.domain.*;
import com.inkgrade.dto.EvaluationDtos.AdminStatsDto;
import com.inkgrade.dto.EvaluationDtos.AuditLogDto;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.dto.UserDtos.*;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.*;
import com.inkgrade.security.CurrentUser;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class UserService {
    private final UserRepository users;
    private final RoleRepository roles;
    private final StudentRepository students;
    private final TeacherRepository teachers;
    private final SubjectRepository subjects;
    private final ExamRepository exams;
    private final SubmissionRepository submissions;
    private final EvaluationRepository evaluations;
    private final AuditLogRepository auditLogs;
    private final PasswordEncoder encoder;
    private final Mapper mapper;
    private final AuditService audit;

    public UserService(UserRepository users, RoleRepository roles, StudentRepository students,
                       TeacherRepository teachers, SubjectRepository subjects, ExamRepository exams,
                       SubmissionRepository submissions, EvaluationRepository evaluations,
                       AuditLogRepository auditLogs, PasswordEncoder encoder, Mapper mapper, AuditService audit) {
        this.users = users;
        this.roles = roles;
        this.students = students;
        this.teachers = teachers;
        this.subjects = subjects;
        this.exams = exams;
        this.submissions = submissions;
        this.evaluations = evaluations;
        this.auditLogs = auditLogs;
        this.encoder = encoder;
        this.mapper = mapper;
        this.audit = audit;
    }

    static String norm(String q) {
        return q == null ? "" : q.trim();
    }

    private UserDto dto(User u) {
        return mapper.user(u, students.findByUserId(u.getId()).orElse(null), teachers.findByUserId(u.getId()).orElse(null));
    }

    @Transactional(readOnly = true)
    public PageResponse<UserDto> list(RoleName role, String q, int page, int size) {
        Pageable p = PageRequest.of(page, Math.min(size, 100), Sort.by("fullName"));
        return PageResponse.of(users.search(role, norm(q), p), this::dto);
    }

    @Transactional(readOnly = true)
    public UserDto get(Long id) {
        return dto(users.findById(id).orElseThrow(() -> ApiException.notFound("User")));
    }

    @Transactional
    public UserDto create(CreateUserRequest r) {
        if (users.existsByUsernameIgnoreCase(r.username())) throw ApiException.conflict("Username already taken");
        if (users.existsByEmailIgnoreCase(r.email())) throw ApiException.conflict("Email already in use");
        User u = new User();
        u.setUsername(r.username().trim());
        u.setEmail(r.email().trim());
        u.setFullName(r.fullName().trim());
        u.setPasswordHash(encoder.encode(r.password()));
        u.setRole(roles.findByName(r.role()).orElseThrow());
        users.save(u);
        switch (r.role()) {
            case STUDENT -> {
                if (r.rollNumber() == null || r.rollNumber().isBlank()) {
                    throw ApiException.badRequest("rollNumber is required for students");
                }
                if (students.existsByRollNumberIgnoreCase(r.rollNumber())) {
                    throw ApiException.conflict("Roll number already in use");
                }
                Student s = new Student();
                s.setUser(u);
                s.setRollNumber(r.rollNumber().trim());
                s.setClassName(r.className());
                students.save(s);
            }
            case TEACHER -> {
                Teacher t = new Teacher();
                t.setUser(u);
                t.setEmployeeId(r.employeeId());
                t.setDepartment(r.department());
                teachers.save(t);
            }
            default -> { }
        }
        audit.log("USER_CREATED", "User", u.getId(), u.getUsername() + " (" + r.role() + ")");
        return dto(u);
    }

    @Transactional
    public UserDto update(Long id, UpdateUserRequest r) {
        User u = users.findById(id).orElseThrow(() -> ApiException.notFound("User"));
        if (!u.getEmail().equalsIgnoreCase(r.email()) && users.existsByEmailIgnoreCase(r.email())) {
            throw ApiException.conflict("Email already in use");
        }
        u.setEmail(r.email().trim());
        u.setFullName(r.fullName().trim());
        if (r.enabled() != null && r.enabled() != u.isEnabled()) {
            setEnabled(u, r.enabled());
        }
        students.findByUserId(id).ifPresent(s -> {
            if (r.rollNumber() != null && !r.rollNumber().isBlank() && !r.rollNumber().equalsIgnoreCase(s.getRollNumber())) {
                if (students.existsByRollNumberIgnoreCase(r.rollNumber())) throw ApiException.conflict("Roll number already in use");
                s.setRollNumber(r.rollNumber().trim());
            }
            s.setClassName(r.className());
        });
        teachers.findByUserId(id).ifPresent(t -> {
            t.setEmployeeId(r.employeeId());
            t.setDepartment(r.department());
        });
        audit.log("USER_UPDATED", "User", id, u.getUsername());
        return dto(u);
    }

    private void setEnabled(User u, boolean enabled) {
        if (!enabled) {
            if (u.getId().equals(CurrentUser.get().getId())) throw ApiException.badRequest("You cannot disable your own account");
            assertNotLastAdmin(u);
        }
        u.setEnabled(enabled);
    }

    private void assertNotLastAdmin(User u) {
        if (u.getRole().getName() == RoleName.ADMIN && u.isEnabled() && users.countByRoleName(RoleName.ADMIN) <= 1) {
            throw ApiException.badRequest("Cannot remove the last administrator");
        }
    }

    @Transactional
    public void resetPassword(Long id, ResetPasswordRequest r) {
        User u = users.findById(id).orElseThrow(() -> ApiException.notFound("User"));
        u.setPasswordHash(encoder.encode(r.newPassword()));
        audit.log("PASSWORD_RESET", "User", id, u.getUsername());
    }

    @Transactional
    public void delete(Long id) {
        User u = users.findById(id).orElseThrow(() -> ApiException.notFound("User"));
        if (u.getId().equals(CurrentUser.get().getId())) throw ApiException.badRequest("You cannot delete your own account");
        assertNotLastAdmin(u);
        students.findByUserId(id).ifPresent(students::delete);
        teachers.findByUserId(id).ifPresent(teachers::delete);
        users.delete(u);
        users.flush();
        audit.log("USER_DELETED", "User", id, u.getUsername());
    }

    @Transactional(readOnly = true)
    public List<RoleDto> roles() {
        return roles.findAll().stream().map(r -> new RoleDto(r.getId(), r.getName(), r.getPermissions())).toList();
    }

    @Transactional
    public RoleDto updatePermissions(Long roleId, UpdatePermissionsRequest r) {
        Role role = roles.findById(roleId).orElseThrow(() -> ApiException.notFound("Role"));
        if (role.getName() == RoleName.ADMIN) throw ApiException.badRequest("Administrator permissions cannot be changed");
        if (role.getName() == RoleName.STUDENT) throw ApiException.badRequest("Students have no assignable permissions");
        for (String p : r.permissions()) {
            if (!Permission.ALL.contains(p)) throw ApiException.badRequest("Unknown permission: " + p);
        }
        role.setPermissions(new HashSet<>(r.permissions()));
        audit.log("ROLE_PERMISSIONS_UPDATED", "Role", roleId, role.getName() + ": " + r.permissions());
        return new RoleDto(role.getId(), role.getName(), role.getPermissions());
    }

    @Transactional(readOnly = true)
    public Set<String> allPermissions() {
        return new HashSet<>(Permission.ALL);
    }

    @Transactional(readOnly = true)
    public AdminStatsDto stats() {
        return new AdminStatsDto(users.countByRoleName(RoleName.STUDENT), users.countByRoleName(RoleName.TEACHER),
                users.countByRoleName(RoleName.ADMIN), subjects.count(), exams.count(), submissions.count(),
                evaluations.count(), evaluations.countByStatus(EvaluationStatus.FINALIZED), auditLogs.count());
    }

    @Transactional(readOnly = true)
    public PageResponse<AuditLogDto> auditLogs(String q, int page, int size) {
        Pageable p = PageRequest.of(page, Math.min(size, 100), Sort.by(Sort.Direction.DESC, "createdAt"));
        return PageResponse.of(auditLogs.search(norm(q), p), a -> new AuditLogDto(a.getId(), a.getUsername(),
                a.getAction(), a.getEntityType(), a.getEntityId(), a.getDetails(), a.getIpAddress(), a.getCreatedAt()));
    }

    @Transactional(readOnly = true)
    public PageResponse<StudentDto> students(String q, int page, int size) {
        Pageable p = PageRequest.of(page, Math.min(size, 100), Sort.by("rollNumber"));
        return PageResponse.of(students.search(norm(q), p), mapper::student);
    }
}
