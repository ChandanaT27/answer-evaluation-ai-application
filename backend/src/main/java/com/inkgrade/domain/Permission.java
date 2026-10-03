package com.inkgrade.domain;

import java.util.List;

public final class Permission {
    public static final String EXAM_MANAGE = "EXAM_MANAGE";
    public static final String SUBJECT_MANAGE = "SUBJECT_MANAGE";
    public static final String SUBMISSION_UPLOAD = "SUBMISSION_UPLOAD";
    public static final String EVALUATION_RUN = "EVALUATION_RUN";
    public static final String EVALUATION_REVIEW = "EVALUATION_REVIEW";
    public static final String EVALUATION_DELETE = "EVALUATION_DELETE";
    public static final String REPORT_DOWNLOAD = "REPORT_DOWNLOAD";

    public static final List<String> ALL = List.of(EXAM_MANAGE, SUBJECT_MANAGE, SUBMISSION_UPLOAD, EVALUATION_RUN,
            EVALUATION_REVIEW, EVALUATION_DELETE, REPORT_DOWNLOAD);

    private Permission() {}
}
