-- MySQL 8+ reference schema for handwritten assessment system
-- Charset supports English + Hindi (UTF-8)

CREATE DATABASE IF NOT EXISTS handwritten_assessment
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE handwritten_assessment;

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role ENUM('student', 'teacher', 'admin') NOT NULL DEFAULT 'student',
    preferred_language VARCHAR(16) NOT NULL DEFAULT 'en',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;

CREATE TABLE assignments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    description TEXT,
    course_code VARCHAR(64),
    due_at DATETIME(6),
    max_score DECIMAL(6,2) NOT NULL DEFAULT 100.00,
    created_by BIGINT UNSIGNED NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_assignments_creator FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE model_answers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    assignment_id BIGINT UNSIGNED NOT NULL,
    question_key VARCHAR(128) NOT NULL,
    reference_text TEXT NOT NULL,
    keywords_json JSON,
    weight DECIMAL(5,4) NOT NULL DEFAULT 1.0000,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_assignment_question (assignment_id, question_key),
    CONSTRAINT fk_model_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE submissions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    assignment_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    original_filename VARCHAR(512),
    stored_path VARCHAR(1024),
    mime_type VARCHAR(128),
    extracted_text TEXT,
    language_hint VARCHAR(16) NOT NULL DEFAULT 'en',
    status ENUM('uploaded', 'ocr_done', 'evaluated', 'failed') NOT NULL DEFAULT 'uploaded',
    batch_id VARCHAR(64),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_sub_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    CONSTRAINT fk_sub_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_submissions_batch (batch_id)
) ENGINE=InnoDB;

CREATE TABLE scores (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    submission_id BIGINT UNSIGNED NOT NULL,
    model_answer_id BIGINT UNSIGNED NOT NULL,
    auto_score DECIMAL(6,2) NOT NULL,
    final_score DECIMAL(6,2),
    semantic_similarity DECIMAL(7,6) NOT NULL,
    keyword_score DECIMAL(7,6) NOT NULL,
    plagiarism_score DECIMAL(7,6),
    explainability_json JSON,
    graded_by_teacher_id BIGINT UNSIGNED,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_score_submission_model (submission_id, model_answer_id),
    CONSTRAINT fk_score_sub FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    CONSTRAINT fk_score_model FOREIGN KEY (model_answer_id) REFERENCES model_answers(id) ON DELETE CASCADE,
    CONSTRAINT fk_score_teacher FOREIGN KEY (graded_by_teacher_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE feedback (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    score_id BIGINT UNSIGNED NOT NULL,
    summary TEXT NOT NULL,
    missing_concepts_json JSON,
    weak_areas_json JSON,
    suggestions_json JSON,
    attention_highlights_json JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_feedback_score (score_id),
    CONSTRAINT fk_feedback_score FOREIGN KEY (score_id) REFERENCES scores(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE plagiarism_flags (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    submission_id BIGINT UNSIGNED NOT NULL,
    compared_submission_id BIGINT UNSIGNED NOT NULL,
    similarity DECIMAL(7,6) NOT NULL,
    note VARCHAR(512),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_plag_sub FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    CONSTRAINT fk_plag_other FOREIGN KEY (compared_submission_id) REFERENCES submissions(id) ON DELETE CASCADE
) ENGINE=InnoDB;
