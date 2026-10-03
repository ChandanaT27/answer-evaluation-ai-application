package com.inkgrade.service;

import com.inkgrade.domain.User;
import com.inkgrade.dto.AuthDtos.*;
import com.inkgrade.exception.ApiException;
import com.inkgrade.repository.StudentRepository;
import com.inkgrade.repository.TeacherRepository;
import com.inkgrade.repository.UserRepository;
import com.inkgrade.security.AppUserDetails;
import com.inkgrade.security.CurrentUser;
import com.inkgrade.security.JwtService;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Service
public class AuthService {
    private final AuthenticationManager authManager;
    private final JwtService jwt;
    private final UserRepository users;
    private final StudentRepository students;
    private final TeacherRepository teachers;
    private final PasswordEncoder encoder;
    private final Mapper mapper;
    private final AuditService audit;

    public AuthService(AuthenticationManager authManager, JwtService jwt, UserRepository users,
                       StudentRepository students, TeacherRepository teachers, PasswordEncoder encoder,
                       Mapper mapper, AuditService audit) {
        this.authManager = authManager;
        this.jwt = jwt;
        this.users = users;
        this.students = students;
        this.teachers = teachers;
        this.encoder = encoder;
        this.mapper = mapper;
        this.audit = audit;
    }

    @Transactional
    public LoginResponse login(LoginRequest req) {
        try {
            var auth = authManager.authenticate(new UsernamePasswordAuthenticationToken(req.username(), req.password()));
            AppUserDetails details = (AppUserDetails) auth.getPrincipal();
            User u = users.findById(details.getId()).orElseThrow();
            u.setLastLoginAt(Instant.now());
            audit.logAs(u.getId(), u.getUsername(), "LOGIN", "User", u.getId(), null);
            return new LoginResponse(jwt.generate(details), "Bearer", jwt.expiresInSeconds(), toDto(u));
        } catch (AuthenticationException e) {
            audit.logAs(null, req.username(), "LOGIN_FAILED", "User", null, null);
            throw new BadCredentialsException("Invalid credentials");
        }
    }

    @Transactional(readOnly = true)
    public com.inkgrade.dto.UserDtos.UserDto me() {
        return toDto(users.findById(CurrentUser.get().getId()).orElseThrow());
    }

    @Transactional
    public void changePassword(ChangePasswordRequest req) {
        User u = users.findById(CurrentUser.get().getId()).orElseThrow();
        if (!encoder.matches(req.currentPassword(), u.getPasswordHash())) {
            throw ApiException.badRequest("Current password is incorrect");
        }
        u.setPasswordHash(encoder.encode(req.newPassword()));
        audit.log("PASSWORD_CHANGED", "User", u.getId(), null);
    }

    com.inkgrade.dto.UserDtos.UserDto toDto(User u) {
        return mapper.user(u, students.findByUserId(u.getId()).orElse(null), teachers.findByUserId(u.getId()).orElse(null));
    }
}
