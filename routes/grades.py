import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import get_db, log_audit
from rbac import login_required, role_required

bp = Blueprint('grades', __name__, url_prefix='/grades')


@bp.route('/')
@login_required
def list_grades():
    db = get_db()
    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'siswa':
        student = db.execute('SELECT id FROM students WHERE user_id = ?', (user_id,)).fetchone()
        if not student:
            db.close()
            flash('Data siswa tidak ditemukan untuk akun Anda.', 'danger')
            return redirect(url_for('dashboard.dashboard'))

        grades = db.execute('''
            SELECT g.*, s.nis, s.name as student_name, u.name as teacher_name
            FROM grades g
            JOIN students s ON g.student_id = s.id
            LEFT JOIN users u ON g.teacher_id = u.id
            WHERE g.student_id = ?
            ORDER BY g.semester, g.subject
        ''', (student['id'],)).fetchall()

    elif role == 'guru':
        grades = db.execute('''
            SELECT g.*, s.nis, s.name as student_name, u.name as teacher_name
            FROM grades g
            JOIN students s ON g.student_id = s.id
            LEFT JOIN users u ON g.teacher_id = u.id
            ORDER BY s.name, g.subject
        ''').fetchall()

    elif role in ('staf_tu', 'kepala_sekolah'):
        grades = db.execute('''
            SELECT g.*, s.nis, s.name as student_name, u.name as teacher_name
            FROM grades g
            JOIN students s ON g.student_id = s.id
            LEFT JOIN users u ON g.teacher_id = u.id
            ORDER BY s.name, g.subject
        ''').fetchall()

    else:
        db.close()
        return render_template('403.html'), 403

    db.close()
    return render_template('grades/list.html', grades=grades, role=role)


@bp.route('/<int:student_id>')
@login_required
def detail(student_id):
    db = get_db()
    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'siswa':
        student_check = db.execute('SELECT id FROM students WHERE user_id = ?', (user_id,)).fetchone()
        if not student_check or student_check['id'] != student_id:
            db.close()
            return render_template('403.html'), 403

    student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        db.close()
        flash('Data siswa tidak ditemukan.', 'danger')
        return redirect(url_for('grades.list_grades'))

    grades = db.execute('''
        SELECT g.*, u.name as teacher_name
        FROM grades g
        LEFT JOIN users u ON g.teacher_id = u.id
        WHERE g.student_id = ?
        ORDER BY g.semester, g.subject
    ''', (student_id,)).fetchall()

    db.close()
    return render_template('grades/detail.html', student=student, grades=grades)


@bp.route('/add', methods=['GET'])
@login_required
@role_required('guru')
def add_get():
    db = get_db()
    students = db.execute('SELECT id, nis, name FROM students ORDER BY name').fetchall()
    db.close()
    return render_template('grades/form.html', students=students)


@bp.route('/add', methods=['POST'])
@login_required
@role_required('guru')
def add_post():
    student_id = request.form.get('student_id')
    subject = request.form.get('subject')
    score = request.form.get('score', type=float)
    semester = request.form.get('semester')

    if not student_id or not subject or score is None or not semester:
        flash('Semua field wajib diisi.', 'danger')
        return redirect(url_for('grades.add_get'))

    db = get_db()

    try:
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO grades (student_id, teacher_id, subject, score, semester)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, session['user_id'], subject, score, semester))
        grade_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO grade_audit_logs (grade_id, user_id, action, old_value, new_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (grade_id, session['user_id'], 'CREATE', None, str(score)))

        db.commit()
        log_audit(session['user_id'], session.get('name'), session.get('role'),
                  'GRADE_CREATE', 'grades',
                  f'Added grade for student_id {student_id}: {subject} = {score}',
                  request.remote_addr)
        flash('Nilai berhasil ditambahkan.', 'success')
        return redirect(url_for('grades.list_grades'))
    except sqlite3.Error as e:
        db.rollback()
        flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('grades.add_get'))
    finally:
        db.close()


@bp.route('/history/<int:grade_id>')
@login_required
@role_required('guru', 'staf_tu', 'kepala_sekolah')
def history(grade_id):
    db = get_db()

    grade = db.execute('''
        SELECT g.*, s.name as student_name, s.nis
        FROM grades g
        JOIN students s ON g.student_id = s.id
        WHERE g.id = ?
    ''', (grade_id,)).fetchone()

    if not grade:
        db.close()
        flash('Data nilai tidak ditemukan.', 'danger')
        return redirect(url_for('grades.list_grades'))

    logs = db.execute('''
        SELECT l.*, u.name as user_name, u.role as user_role
        FROM grade_audit_logs l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.grade_id = ?
        ORDER BY l.timestamp DESC
    ''', (grade_id,)).fetchall()

    db.close()
    return render_template('grades/history.html', grade=grade, logs=logs)
