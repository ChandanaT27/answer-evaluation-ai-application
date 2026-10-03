package com.inkgrade.security;

import com.inkgrade.exception.ApiException;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

public final class CurrentUser {
    private CurrentUser() {}

    public static AppUserDetails get() {
        Authentication a = SecurityContextHolder.getContext().getAuthentication();
        if (a == null || !(a.getPrincipal() instanceof AppUserDetails d)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Authentication required");
        }
        return d;
    }

    public static boolean isAdmin() { return "ADMIN".equals(get().getRole()); }
    public static boolean isTeacher() { return "TEACHER".equals(get().getRole()); }
    public static boolean isStudent() { return "STUDENT".equals(get().getRole()); }
}
