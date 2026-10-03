package com.inkgrade.service;

import com.inkgrade.domain.AuditLog;
import com.inkgrade.repository.AuditLogRepository;
import com.inkgrade.security.AppUserDetails;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Service
public class AuditService {
    private final AuditLogRepository repo;

    public AuditService(AuditLogRepository repo) {
        this.repo = repo;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void log(String action, String entityType, Long entityId, String details) {
        AuditLog l = new AuditLog();
        l.setAction(action);
        l.setEntityType(entityType);
        l.setEntityId(entityId);
        l.setDetails(details == null ? null : details.length() > 1000 ? details.substring(0, 1000) : details);
        Authentication a = SecurityContextHolder.getContext().getAuthentication();
        if (a != null && a.getPrincipal() instanceof AppUserDetails u) {
            l.setUserId(u.getId());
            l.setUsername(u.getUsername());
        }
        RequestAttributes attrs = RequestContextHolder.getRequestAttributes();
        if (attrs instanceof ServletRequestAttributes sra) {
            l.setIpAddress(sra.getRequest().getRemoteAddr());
        }
        repo.save(l);
    }

    public void logAs(Long userId, String username, String action, String entityType, Long entityId, String details) {
        AuditLog l = new AuditLog();
        l.setUserId(userId);
        l.setUsername(username);
        l.setAction(action);
        l.setEntityType(entityType);
        l.setEntityId(entityId);
        l.setDetails(details);
        repo.save(l);
    }
}
