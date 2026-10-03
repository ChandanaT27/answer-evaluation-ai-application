package com.inkgrade.repository;

import com.inkgrade.domain.RoleName;
import com.inkgrade.domain.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsernameIgnoreCase(String username);
    boolean existsByUsernameIgnoreCase(String username);
    boolean existsByEmailIgnoreCase(String email);
    long countByRoleName(RoleName name);

    @Query("""
            select u from User u where (:role is null or u.role.name = :role)
            and (:q = '' or lower(u.username) like lower(concat('%', :q, '%'))
                 or lower(u.fullName) like lower(concat('%', :q, '%'))
                 or lower(u.email) like lower(concat('%', :q, '%')))
            """)
    Page<User> search(@Param("role") RoleName role, @Param("q") String q, Pageable pageable);
}
