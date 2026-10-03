package com.inkgrade.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@ConfigurationProperties(prefix = "app")
public record AppProperties(Jwt jwt, Cors cors, Storage storage, Ai ai, Admin admin, boolean seedDemo) {
    public record Jwt(String secret, long expirationMinutes) {}
    public record Cors(List<String> allowedOrigins) {}
    public record Storage(String root) {}
    public record Ai(String baseUrl, String apiKey, int timeoutSeconds) {}
    public record Admin(String username, String password, String email) {}
}
