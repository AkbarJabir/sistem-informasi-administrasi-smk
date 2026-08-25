"""
Database module for Sistem Informasi Administrasi SMK.
Schema based on PRD Section 9.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smk_admin.db')


def get_db():
    """Get database connection with row factory."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    """Initialize database schema."""
    db = get_db()
    cursor = db.cursor()

    # --- Users ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('siswa','guru','staf_tu','kepala_sekolah','mitra_dudi')),
            mfa_enabled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- Students ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nis TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            class TEXT NOT NULL,
            major TEXT NOT NULL,
            enrollment_year INTEGER NOT NULL,
            graduation_year INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # --- Grades ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            score REAL NOT NULL,
            semester TEXT DEFAULT '1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    ''')

    # --- Grade Audit Logs ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grade_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            old_value TEXT,
            new_value TEXT,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grade_id) REFERENCES grades(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # --- Certificates (Ijazah) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'ijazah',
            document_name TEXT,
            document_hash TEXT,
            blockchain_tx_hash TEXT,
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','pending_approval','approved','rejected')),
            issued_at TIMESTAMP,
            approved_by INTEGER,
            approved_at TIMESTAMP,
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pdf_filename TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (approved_by) REFERENCES users(id)
        )
    ''')

    # --- Companies ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wallet_id TEXT
        )
    ''')

    # --- Internship Certificates (Sertifikat PKL) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS internship_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            period_start DATE,
            period_end DATE,
            document_hash TEXT,
            digital_signature TEXT,
            wallet_id TEXT,
            blockchain_tx_hash TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')

    # --- General Audit Logs ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            user_role TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            detail TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # --- Blockchain Records ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blockchain_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_index INTEGER NOT NULL,
            previous_hash TEXT NOT NULL,
            document_hash TEXT NOT NULL,
            document_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            issuer TEXT,
            tx_hash TEXT UNIQUE
        )
    ''')

    db.commit()
    db.close()


def seed_data():
    """Seed demo data if users table is empty."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        db.close()
        return

    # ── Demo Users ──
    users = [
        ('Andi Pratama', 'siswa@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Budi Santoso', 'guru@smk.sch.id', generate_password_hash('guru123'), 'guru', 0),
        ('Citra Dewi', 'tu@smk.sch.id', generate_password_hash('tu123'), 'staf_tu', 1),
        ('Dr. Hendra Wijaya', 'kepsek@smk.sch.id', generate_password_hash('kepsek123'), 'kepala_sekolah', 1),
        ('PT Maju Bersama', 'dudi@industry.co.id', generate_password_hash('dudi123'), 'mitra_dudi', 0),
    ]
    cursor.executemany(
        "INSERT INTO users (name, email, password_hash, role, mfa_enabled) VALUES (?, ?, ?, ?, ?)",
        users
    )

    # Additional students
    additional_students_users = [
        ('Dewi Lestari', 'dewi@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Eko Saputra', 'eko@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Fitri Handayani', 'fitri@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Galih Permana', 'galih@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Hani Rahayu', 'hani@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Irfan Maulana', 'irfan@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Joko Widodo', 'joko@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Kartika Sari', 'kartika@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
        ('Lukman Hakim', 'lukman@smk.sch.id', generate_password_hash('siswa123'), 'siswa', 0),
    ]
    cursor.executemany(
        "INSERT INTO users (name, email, password_hash, role, mfa_enabled) VALUES (?, ?, ?, ?, ?)",
        additional_students_users
    )

    # ── Students ──
    students = [
        (1, '2024001', 'Andi Pratama', 'XII RPL 1', 'Rekayasa Perangkat Lunak', 2021, 2024),
        (6, '2024002', 'Dewi Lestari', 'XII RPL 1', 'Rekayasa Perangkat Lunak', 2021, 2024),
        (7, '2024003', 'Eko Saputra', 'XII TKJ 1', 'Teknik Komputer dan Jaringan', 2021, 2024),
        (8, '2024004', 'Fitri Handayani', 'XII TKJ 1', 'Teknik Komputer dan Jaringan', 2021, 2024),
        (9, '2024005', 'Galih Permana', 'XII RPL 2', 'Rekayasa Perangkat Lunak', 2022, 2025),
        (10, '2024006', 'Hani Rahayu', 'XII RPL 2', 'Rekayasa Perangkat Lunak', 2022, 2025),
        (11, '2024007', 'Irfan Maulana', 'XII MM 1', 'Multimedia', 2022, 2025),
        (12, '2024008', 'Joko Widodo', 'XII MM 1', 'Multimedia', 2022, 2025),
        (13, '2024009', 'Kartika Sari', 'XI RPL 1', 'Rekayasa Perangkat Lunak', 2023, None),
        (14, '2024010', 'Lukman Hakim', 'XI TKJ 1', 'Teknik Komputer dan Jaringan', 2023, None),
    ]
    cursor.executemany(
        "INSERT INTO students (user_id, nis, name, class, major, enrollment_year, graduation_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
        students
    )

    # ── Grades ──
    subjects = ['Matematika', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pemrograman Web', 'Basis Data', 'Jaringan Komputer']
    for student_id in range(1, 11):
        for subj in subjects[:4]:
            score = round(random.uniform(70, 95), 1)
            cursor.execute(
                "INSERT INTO grades (student_id, teacher_id, subject, score, semester) VALUES (?, ?, ?, ?, ?)",
                (student_id, 2, subj, score, 'Ganjil 2023/2024')
            )

    # ── Companies ──
    cursor.execute(
        "INSERT INTO companies (name, wallet_id) VALUES (?, ?)",
        ('PT Maju Bersama', '0x1a2b3c4d5e6f7890abcdef1234567890abcdef12')
    )
    cursor.execute(
        "INSERT INTO companies (name, wallet_id) VALUES (?, ?)",
        ('CV Teknologi Nusantara', '0x9876543210fedcba9876543210fedcba98765432')
    )

    # ── Internship Certificates ──
    cursor.execute(
        """INSERT INTO internship_certificates
        (student_id, company_id, period_start, period_end, document_hash, digital_signature, wallet_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (1, 1, '2023-07-01', '2023-12-31',
         'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
         'sig_demo_001', '0x1a2b3c4d5e6f7890abcdef1234567890abcdef12', 'active')
    )

    db.commit()
    db.close()


def log_audit(user_id, user_name, user_role, action, resource, detail, ip_address='127.0.0.1'):
    """Record an audit log entry."""
    db = get_db()
    db.execute(
        """INSERT INTO audit_logs (user_id, user_name, user_role, action, resource, detail, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, user_name, user_role, action, resource, detail, ip_address)
    )
    db.commit()
    db.close()
