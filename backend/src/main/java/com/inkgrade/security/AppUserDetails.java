package com.inkgrade.security;

import com.inkgrade.domain.User;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class AppUserDetails implements UserDetails {
    private final Long id;
    private final String username;
    private final String passwordHash;
    private final boolean enabled;
    private final String role;
    private final List<GrantedAuthority> authorities = new ArrayList<>();

    public AppUserDetails(User user) {
        this.id = user.getId();
        this.username = user.getUsername();
        this.passwordHash = user.getPasswordHash();
        this.enabled = user.isEnabled();
        this.role = user.getRole().getName().name();
        authorities.add(new SimpleGrantedAuthority("ROLE_" + role));
        user.getRole().getPermissions().forEach(p -> authorities.add(new SimpleGrantedAuthority(p)));
    }

    public Long getId() { return id; }
    public String getRole() { return role; }
    @Override public Collection<? extends GrantedAuthority> getAuthorities() { return authorities; }
    @Override public String getPassword() { return passwordHash; }
    @Override public String getUsername() { return username; }
    @Override public boolean isEnabled() { return enabled; }
}
