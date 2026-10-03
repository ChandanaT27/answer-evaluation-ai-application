package com.inkgrade.config;

import com.inkgrade.domain.*;
import com.inkgrade.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;

@Component
public class DataInitializer implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final RoleRepository roles;
    private final UserRepository users;
    private final StudentRepository students;
    private final TeacherRepository teachers;
    private final SubmissionRepository submissions;
    private final PasswordEncoder encoder;
    private final AppProperties props;

    public DataInitializer(RoleRepository roles, UserRepository users, StudentRepository students,
                           TeacherRepository teachers, SubmissionRepository submissions, PasswordEncoder encoder,
                           AppProperties props) {
        this.roles = roles;
        this.users = users;
        this.students = students;
        this.teachers = teachers;
        this.submissions = submissions;
        this.encoder = encoder;
        this.props = props;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        for (RoleName n : RoleName.values()) {
            Role r = roles.findByName(n).orElseGet(() -> {
                Role nr = new Role();
                nr.setName(n);
                if (n == RoleName.TEACHER) nr.setPermissions(new HashSet<>(Permission.ALL));
                return nr;
            });
            if (n == RoleName.ADMIN) r.setPermissions(new HashSet<>(Permission.ALL));
            roles.save(r);
        }
        if (users.countByRoleName(RoleName.ADMIN) == 0) {
            var a = props.admin();
            createUser(a.username(), a.email(), "System Administrator", a.password(), RoleName.ADMIN);
            log.info("Created default administrator '{}'", a.username());
        }
        if (props.seedDemo() && !users.existsByUsernameIgnoreCase("teacher1")) {
            User t = createUser("teacher1", "teacher1@inkgrade.local", "Demo Teacher", "Teacher@123", RoleName.TEACHER);
            Teacher teacher = new Teacher();
            teacher.setUser(t);
            teacher.setEmployeeId("T-001");
            teacher.setDepartment("Science");
            teachers.save(teacher);
            for (int i = 1; i <= 2; i++) {
                User su = createUser("student" + i, "student" + i + "@inkgrade.local", "Demo Student " + i,
                        "Student@123", RoleName.STUDENT);
                Student s = new Student();
                s.setUser(su);
                s.setRollNumber("R-00" + i);
                s.setClassName("10-A");
                students.save(s);
            }
            log.info("Seeded demo users: teacher1/Teacher@123, student1..2/Student@123");
        }
        // anything left EVALUATING by a crash/restart can never complete
        List<Submission> stuck = submissions.findAll().stream().filter(s -> s.getStatus() == SubmissionStatus.EVALUATING).toList();
        stuck.forEach(s -> {
            s.setStatus(SubmissionStatus.FAILED);
            s.setErrorMessage("Evaluation interrupted by a server restart; please start it again");
        });
    }

    private User createUser(String username, String email, String name, String password, RoleName role) {
        User u = new User();
        u.setUsername(username);
        u.setEmail(email);
        u.setFullName(name);
        u.setPasswordHash(encoder.encode(password));
        u.setRole(roles.findByName(role).orElseThrow());
        return users.save(u);
    }
}
