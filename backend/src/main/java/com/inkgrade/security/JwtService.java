package com.inkgrade.security;

import com.inkgrade.config.AppProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.Optional;

@Service
public class JwtService {
    private final SecretKey key;
    private final long expirationMinutes;

    public JwtService(AppProperties props) {
        byte[] bytes = props.jwt().secret().getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) {
            throw new IllegalStateException("app.jwt.secret must be at least 32 bytes");
        }
        this.key = Keys.hmacShaKeyFor(bytes);
        this.expirationMinutes = props.jwt().expirationMinutes();
    }

    public String generate(AppUserDetails user) {
        Instant now = Instant.now();
        return Jwts.builder().subject(user.getUsername()).claim("uid", user.getId()).claim("role", user.getRole())
                .issuedAt(Date.from(now)).expiration(Date.from(now.plusSeconds(expirationMinutes * 60)))
                .signWith(key).compact();
    }

    public long expiresInSeconds() {
        return expirationMinutes * 60;
    }

    public Optional<String> validateAndGetUsername(String token) {
        try {
            Claims c = Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
            return Optional.ofNullable(c.getSubject());
        } catch (JwtException | IllegalArgumentException e) {
            return Optional.empty();
        }
    }
}
