package com.inkgrade.dto;

import com.inkgrade.domain.RoleName;
import jakarta.validation.constraints.*;

import java.time.Instant;
import java.util.Set;

public final class UserDtos {
    private UserDtos() {}

    public record UserDto(Long id, String username, String email, String fullName, RoleName role, boolean enabled,
                          String rollNumber, String className, String employeeId, String department,
                          Set<String> permissions, Instant createdAt, Instant lastLoginAt) {}

    public record CreateUserRequest(
            @NotBlank @Size(min = 3, max = 60) @Pattern(regexp = "[A-Za-z0-9._-]+", message = "letters, digits, . _ - only") String username,
            @NotBlank @Email @Size(max = 120) String email,
            @NotBlank @Size(max = 120) String fullName,
            @NotBlank @Size(min = 8, max = 100) String password,
            @NotNull RoleName role,
            @Size(max = 40) String rollNumber,
            @Size(max = 60) String className,
            @Size(max = 40) String employeeId,
            @Size(max = 80) String department) {}

    public record UpdateUserRequest(
            @NotBlank @Email @Size(max = 120) String email,
            @NotBlank @Size(max = 120) String fullName,
            Boolean enabled,
            @Size(max = 40) String rollNumber,
            @Size(max = 60) String className,
            @Size(max = 40) String employeeId,
            @Size(max = 80) String department) {}

    public record ResetPasswordRequest(@NotBlank @Size(min = 8, max = 100) String newPassword) {}

    public record RoleDto(Long id, RoleName name, Set<String> permissions) {}

    public record UpdatePermissionsRequest(@NotNull Set<String> permissions) {}

    public record StudentDto(Long id, Long userId, String fullName, String rollNumber, String className) {}
}
