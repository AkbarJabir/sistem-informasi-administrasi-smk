import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
from werkzeug.utils import secure_filename
from database import get_db, log_audit
from rbac import login_required, role_required
from blockchain import compute_sha256

bp = Blueprint('certificates', __name__, url_prefix='/certificates')

@bp.route('/')
@login_required
@role_required('staf_tu', 'kepala_sekolah', 'siswa')
def list_certificates():
    db = get_db()
    if session['role'] == 'siswa':
        student = db.execute('SELECT id FROM students WHERE user_id = ?', (session['user_id'],)).fetchone()
        if not student:
            flash('Data siswa tidak ditemukan.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        certs = db.execute('''
            SELECT c.*, s.name as student_name, s.nis 
            FROM certificates c 
            JOIN students s ON c.student_id = s.id 
            WHERE c.student_id = ?
            ORDER BY c.created_at DESC
        ''', (student['id'],)).fetchall()
    else:
        certs = db.execute('''
            SELECT c.*, s.name as student_name, s.nis 
            FROM certificates c 
            JOIN students s ON c.student_id = s.id 
            ORDER BY c.created_at DESC
        ''').fetchall()
    
    return render_template('certificates/list.html', certificates=certs)

@bp.route('/<int:id>')
@login_required
@role_required('staf_tu', 'kepala_sekolah', 'siswa')
def detail(id):
    db = get_db()
    cert = db.execute('''
        SELECT c.*, s.name as student_name, s.nis, 
               u.name as approved_by_name
        FROM certificates c
        JOIN students s ON c.student_id = s.id
        LEFT JOIN users u ON c.approved_by = u.id
        WHERE c.id = ?
    ''', (id,)).fetchone()
    
    if not cert:
        flash('Ijazah tidak ditemukan.', 'danger')
        return redirect(url_for('certificates.list_certificates'))
        
    if session['role'] == 'siswa':
        student = db.execute('SELECT id FROM students WHERE user_id = ?', (session['user_id'],)).fetchone()
        if not student or cert['student_id'] != student['id']:
            flash('Akses ditolak.', 'danger')
            return redirect(url_for('certificates.list_certificates'))
            
    return render_template('certificates/detail.html', cert=cert)

@bp.route('/<int:id>/file')
@login_required
@role_required('staf_tu', 'kepala_sekolah', 'siswa')
def view_file(id):
    db = get_db()
    cert = db.execute('SELECT * FROM certificates WHERE id = ?', (id,)).fetchone()
    if not cert or not cert['pdf_filename']:
        flash('File dokumen tidak ditemukan.', 'danger')
        return redirect(url_for('certificates.list_certificates'))
        
    if session['role'] == 'siswa':
        student = db.execute('SELECT id FROM students WHERE user_id = ?', (session['user_id'],)).fetchone()
        if not student or cert['student_id'] != student['id']:
            flash('Akses ditolak.', 'danger')
            return redirect(url_for('certificates.list_certificates'))
            
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    return send_from_directory(upload_dir, cert['pdf_filename'], as_attachment=False)

@bp.route('/create', methods=['GET'])
@login_required
@role_required('staf_tu')
def create_form():
    db = get_db()
    students = db.execute('SELECT id, nis, name FROM students ORDER BY name').fetchall()
    return render_template('certificates/create.html', students=students)

@bp.route('/create', methods=['POST'])
@login_required
@role_required('staf_tu')
def create():
    student_id = request.form.get('student_id')
    document_name = request.form.get('document_name')
    cert_type = request.form.get('type', 'ijazah')
    
    if not student_id or not document_name:
        flash('Data siswa dan nama dokumen wajib diisi.', 'danger')
        return redirect(url_for('certificates.create_form'))
        
    if 'document_file' not in request.files:
        flash('File ijazah wajib diunggah.', 'danger')
        return redirect(url_for('certificates.create_form'))
        
    file = request.files['document_file']
    if file.filename == '':
        flash('File ijazah wajib dipilih.', 'danger')
        return redirect(url_for('certificates.create_form'))
        
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    doc_hash = compute_sha256(file_bytes)
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO certificates (student_id, document_name, type, status, document_hash, pdf_filename)
        VALUES (?, ?, ?, 'draft', ?, ?)
    ''', (student_id, document_name, cert_type, doc_hash, filename))
    db.commit()
    
    cert_id = cursor.lastrowid
    
    log_audit(session['user_id'], session['name'], session['role'], 
              'CREATE', 'certificates', f'Created draft certificate for student_id {student_id}', 
              request.remote_addr)
              
    flash('Draft Ijazah berhasil dibuat.', 'success')
    return redirect(url_for('certificates.detail', id=cert_id))

@bp.route('/<int:id>/submit', methods=['POST'])
@login_required
@role_required('staf_tu')
def submit(id):
    db = get_db()
    cert = db.execute('SELECT * FROM certificates WHERE id = ?', (id,)).fetchone()
    
    if not cert:
        flash('Ijazah tidak ditemukan.', 'danger')
        return redirect(url_for('certificates.list_certificates'))
        
    if cert['status'] != 'draft':
        flash('Hanya ijazah dengan status draft yang dapat disubmit.', 'danger')
        return redirect(url_for('certificates.detail', id=id))
        
    if not cert['document_hash']:
        flash('Dokumen hash tidak ditemukan, harap unggah ulang ijazah.', 'danger')
        return redirect(url_for('certificates.detail', id=id))
        
    db.execute('UPDATE certificates SET status = "pending_approval" WHERE id = ?', (id,))
    db.commit()
    
    log_audit(session['user_id'], session['name'], session['role'], 
              'SUBMIT_APPROVAL', 'certificates', f'Submitted certificate ID {id} for approval', 
              request.remote_addr)
              
    flash('Ijazah berhasil disubmit untuk persetujuan.', 'success')
    return redirect(url_for('certificates.list_certificates'))
