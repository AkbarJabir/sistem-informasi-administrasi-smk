from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db, log_audit
from rbac import login_required, role_required
from blockchain import compute_sha256, smart_contract
import datetime
import hashlib

bp = Blueprint('internship', __name__, url_prefix='/internship')

@bp.route('/')
@login_required
@role_required('staf_tu', 'kepala_sekolah', 'mitra_dudi')
def list_internships():
    db = get_db()
    
    query = """
    SELECT ic.*, s.name as student_name, s.nis, c.name as company_name 
    FROM internship_certificates ic
    JOIN students s ON ic.student_id = s.id
    JOIN companies c ON ic.company_id = c.id
    """
    
    certs = db.execute(query).fetchall()
    return render_template('internship/list.html', certs=certs)

@bp.route('/<int:id>')
@login_required
@role_required('staf_tu', 'kepala_sekolah', 'mitra_dudi')
def detail(id):
    db = get_db()
    cert = db.execute("""
    SELECT ic.*, s.name as student_name, s.nis, c.name as company_name, c.wallet_id
    FROM internship_certificates ic
    JOIN students s ON ic.student_id = s.id
    JOIN companies c ON ic.company_id = c.id
    WHERE ic.id = ?
    """, (id,)).fetchone()
    
    if not cert:
        flash('Sertifikat PKL tidak ditemukan.', 'danger')
        return redirect(url_for('internship.list_internships'))
        
    return render_template('internship/detail.html', cert=cert)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('staf_tu')
def create():
    db = get_db()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        company_id = request.form.get('company_id')
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        
        if not all([student_id, company_id, period_start, period_end]):
            flash('Semua kolom wajib diisi.', 'danger')
            return redirect(request.url)
            
        student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        company = db.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        
        # Generate document_hash
        data_to_hash = f"{student['nis']}{company['name']}{period_start}{period_end}".encode('utf-8')
        doc_hash = compute_sha256(data_to_hash)
        digital_signature = f"sig_{doc_hash[:16]}"
        
        # Issue on blockchain
        bc_result = smart_contract.issue_certificate(
            issuer_role=session.get('role'),
            issuer_name=session.get('name'),
            document_hash=doc_hash,
            document_type='sertifikat_pkl'
        )
        
        blockchain_tx_hash = bc_result.get('tx_hash') if bc_result.get('success') else None
        
        cursor = db.execute("""
        INSERT INTO internship_certificates 
        (student_id, company_id, period_start, period_end, document_hash, digital_signature, wallet_id, blockchain_tx_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, company_id, period_start, period_end, doc_hash, digital_signature, company['wallet_id'], blockchain_tx_hash))
        
        db.commit()
        
        log_audit(
            session.get('user_id'), session.get('name'), session.get('role'),
            'CREATE', 'internship_certificates', f"Created PKL cert for student_id {student_id}", request.remote_addr
        )
        
        flash('Sertifikat PKL berhasil dibuat dan dicatat di blockchain.', 'success')
        return redirect(url_for('internship.list_internships'))
        
    students = db.execute("SELECT * FROM students").fetchall()
    companies = db.execute("SELECT * FROM companies").fetchall()
    
    return render_template('internship/form.html', students=students, companies=companies)
