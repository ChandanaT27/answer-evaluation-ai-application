package com.inkgrade.web;

import com.inkgrade.dto.AuthDtos.*;
import com.inkgrade.dto.UserDtos.UserDto;
import com.inkgrade.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService auth;

    public AuthController(AuthService auth) {
        this.auth = auth;
    }

    @PostMapping("/login")
    public LoginResponse login(@Valid @RequestBody LoginRequest r) {
        return auth.login(r);
    }

    @GetMapping("/me")
    public UserDto me() {
        return auth.me();
    }

    @PostMapping("/change-password")
    public ResponseEntity<Void> changePassword(@Valid @RequestBody ChangePasswordRequest r) {
        auth.changePassword(r);
        return ResponseEntity.noContent().build();
    }
}
