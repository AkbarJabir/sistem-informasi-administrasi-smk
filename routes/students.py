import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from database import get_db, log_audit
from rbac import login_required, role_required

bp = Blueprint('students', __name__, url_prefix='/students')

@bp.route('/')
@login_required
@role_required('staf_tu', 'guru', 'kepala_sekolah')
def list_students():
    q = request.args.get('q', '')
    db = get_db()
    if q:
        students = db.execute('''
            SELECT * FROM students 
            WHERE name LIKE ? OR nis LIKE ? OR class LIKE ? OR major LIKE ?
            ORDER BY name
        ''', (f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()
    else:
        students = db.execute('SELECT * FROM students ORDER BY name').fetchall()
    db.close()
    return render_template('students/list.html', students=students, q=q)

@bp.route('/<int:id>')
@login_required
@role_required('staf_tu', 'guru', 'kepala_sekolah')
def detail(id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (id,)).fetchone()
    if not student:
        db.close()
        flash('Data siswa tidak ditemukan.', 'danger')
        return redirect(url_for('students.list_students'))
        
    grades = db.execute('''
        SELECT g.*, u.name as teacher_name 
        FROM grades g 
        LEFT JOIN users u ON g.teacher_id = u.id
        WHERE g.student_id = ?
        ORDER BY g.semester, g.subject
    ''', (id,)).fetchall()
    db.close()
    return render_template('students/detail.html', student=student, grades=grades)

@bp.route('/add', methods=['GET'])
@login_required
@role_required('staf_tu')
def add_get():
    return render_template('students/form.html', mode='add')

@bp.route('/add', methods=['POST'])
@login_required
@role_required('staf_tu')
def add_post():
    nis = request.form.get('nis')
    name = request.form.get('name')
    kelas = request.form.get('class')
    major = request.form.get('major')
    enrollment_year = request.form.get('enrollment_year')
    graduation_year = request.form.get('graduation_year')
    
    if not nis or not name:
        flash('NIS dan Nama wajib diisi.', 'danger')
        return redirect(url_for('students.add_get'))
        
    db = get_db()
    
    try:
        # Create user account (email = nis@smk.sch.id, password = nis + '123')
        email = f'{nis}@smk.sch.id'
        password_hash = generate_password_hash(nis + '123')
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, mfa_enabled) 
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, password_hash, 'siswa', 0))
        user_id = cursor.lastrowid
        
        # Create student record
        cursor.execute('''
            INSERT INTO students (user_id, nis, name, class, major, enrollment_year, graduation_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, nis, name, kelas, major, enrollment_year, graduation_year or None))
        
        db.commit()
        log_audit(session['user_id'], session.get('name'), session.get('role'),
                  'CREATE', 'students', f'Added student {name} (NIS: {nis})', request.remote_addr)
        flash(f'Data siswa berhasil ditambahkan. Akun: {email} / {nis}123', 'success')
        return redirect(url_for('students.list_students'))
    except sqlite3.IntegrityError:
        db.rollback()
        flash('NIS atau Email sudah digunakan.', 'danger')
        return redirect(url_for('students.add_get'))
    finally:
        db.close()

@bp.route('/<int:id>/edit', methods=['GET'])
@login_required
@role_required('staf_tu')
def edit_get(id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (id,)).fetchone()
    db.close()
    if not student:
        flash('Data siswa tidak ditemukan.', 'danger')
        return redirect(url_for('students.list_students'))
    return render_template('students/form.html', mode='edit', student=student)

@bp.route('/<int:id>/edit', methods=['POST'])
@login_required
@role_required('staf_tu')
def edit_post(id):
    nis = request.form.get('nis')
    name = request.form.get('name')
    kelas = request.form.get('class')
    major = request.form.get('major')
    enrollment_year = request.form.get('enrollment_year')
    graduation_year = request.form.get('graduation_year')
    
    db = get_db()
    try:
        db.execute('''
            UPDATE students 
            SET nis = ?, name = ?, class = ?, major = ?, enrollment_year = ?, graduation_year = ?
            WHERE id = ?
        ''', (nis, name, kelas, major, enrollment_year, graduation_year or None, id))
        db.commit()
        log_audit(session['user_id'], session.get('name'), session.get('role'),
                  'UPDATE', 'students', f'Updated student {id}', request.remote_addr)
        flash('Data siswa berhasil diubah.', 'success')
        return redirect(url_for('students.detail', id=id))
    except sqlite3.IntegrityError:
        db.rollback()
        flash('NIS sudah digunakan.', 'danger')
        return redirect(url_for('students.edit_get', id=id))
    finally:
        db.close()
