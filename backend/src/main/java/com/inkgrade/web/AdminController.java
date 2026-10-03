package com.inkgrade.web;

import com.inkgrade.domain.RoleName;
import com.inkgrade.dto.EvaluationDtos.AdminStatsDto;
import com.inkgrade.dto.EvaluationDtos.AuditLogDto;
import com.inkgrade.dto.PageResponse;
import com.inkgrade.dto.UserDtos.*;
import com.inkgrade.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Set;

@RestController
@RequestMapping("/api/admin")
public class AdminController {
    private final UserService users;

    public AdminController(UserService users) {
        this.users = users;
    }

    @GetMapping("/users")
    public PageResponse<UserDto> list(@RequestParam(required = false) RoleName role,
                                      @RequestParam(required = false) String q,
                                      @RequestParam(defaultValue = "0") int page,
                                      @RequestParam(defaultValue = "20") int size) {
        return users.list(role, q, Math.max(page, 0), Math.max(size, 1));
    }

    @GetMapping("/users/{id}")
    public UserDto get(@PathVariable Long id) {
        return users.get(id);
    }

    @PostMapping("/users")
    @ResponseStatus(HttpStatus.CREATED)
    public UserDto create(@Valid @RequestBody CreateUserRequest r) {
        return users.create(r);
    }

    @PutMapping("/users/{id}")
    public UserDto update(@PathVariable Long id, @Valid @RequestBody UpdateUserRequest r) {
        return users.update(id, r);
    }

    @PostMapping("/users/{id}/reset-password")
    public ResponseEntity<Void> reset(@PathVariable Long id, @Valid @RequestBody ResetPasswordRequest r) {
        users.resetPassword(id, r);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        users.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/roles")
    public List<RoleDto> roles() {
        return users.roles();
    }

    @GetMapping("/permissions")
    public Set<String> permissions() {
        return users.allPermissions();
    }

    @PutMapping("/roles/{id}/permissions")
    public RoleDto updatePermissions(@PathVariable Long id, @Valid @RequestBody UpdatePermissionsRequest r) {
        return users.updatePermissions(id, r);
    }

    @GetMapping("/stats")
    public AdminStatsDto stats() {
        return users.stats();
    }

    @GetMapping("/audit-logs")
    public PageResponse<AuditLogDto> audit(@RequestParam(required = false) String q,
                                           @RequestParam(defaultValue = "0") int page,
                                           @RequestParam(defaultValue = "30") int size) {
        return users.auditLogs(q, Math.max(page, 0), Math.max(size, 1));
    }
}
