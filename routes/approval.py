import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database import get_db, log_audit
from rbac import login_required, role_required
from blockchain import smart_contract

bp = Blueprint('approval', __name__, url_prefix='/approval')

@bp.route('/')
@login_required
@role_required('kepala_sekolah')
def list_approvals():
    db = get_db()
    pending = db.execute('''
        SELECT c.*, s.name as student_name, s.nis 
        FROM certificates c 
        JOIN students s ON c.student_id = s.id 
        WHERE c.status = 'pending_approval'
        ORDER BY c.created_at ASC
    ''').fetchall()
    
    history = db.execute('''
        SELECT c.*, s.name as student_name, s.nis 
        FROM certificates c 
        JOIN students s ON c.student_id = s.id 
        WHERE c.status IN ('approved', 'rejected')
        ORDER BY c.approved_at DESC
        LIMIT 50
    ''').fetchall()
    
    return render_template('approval/list.html', pending=pending, history=history)

@bp.route('/<int:id>')
@login_required
@role_required('kepala_sekolah')
def detail(id):
    db = get_db()
    cert = db.execute('''
        SELECT c.*, s.name as student_name, s.nis
        FROM certificates c
        JOIN students s ON c.student_id = s.id
        WHERE c.id = ?
    ''', (id,)).fetchone()
    
    if not cert:
        flash('Ijazah tidak ditemukan.', 'danger')
        return redirect(url_for('approval.list_approvals'))
        
    return render_template('approval/detail.html', cert=cert)

@bp.route('/<int:id>/approve', methods=['POST'])
@login_required
@role_required('kepala_sekolah')
def approve(id):
    db = get_db()
    cert = db.execute('SELECT * FROM certificates WHERE id = ?', (id,)).fetchone()
    
    if not cert or cert['status'] != 'pending_approval':
        flash('Ijazah tidak valid atau tidak dalam status menunggu persetujuan.', 'danger')
        return redirect(url_for('approval.list_approvals'))
        
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Blockchain recording
    result = smart_contract.issue_certificate(
        issuer_role=session['role'],
        issuer_name=session['name'],
        document_hash=cert['document_hash'],
        document_type=cert['type']
    )
    
    if result.get('success'):
        tx_hash = result.get('tx_hash')
        db.execute('''
            UPDATE certificates 
            SET status = 'approved', approved_by = ?, approved_at = ?, issued_at = ?, blockchain_tx_hash = ?
            WHERE id = ?
        ''', (session['user_id'], now, now, tx_hash, id))
        db.commit()
        
        log_audit(session['user_id'], session['name'], session['role'], 
                  'APPROVE', 'certificates', f'Approved certificate ID {id}, tx: {tx_hash}', 
                  request.remote_addr)
                  
        flash(f'Ijazah berhasil disetujui dan dicatat ke blockchain! Tx: {tx_hash}', 'success')
    else:
        flash(f"Gagal mencatat ke blockchain: {result.get('error', 'Unknown error')}", 'danger')
        
    return redirect(url_for('approval.list_approvals'))

@bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@role_required('kepala_sekolah')
def reject(id):
    db = get_db()
    cert = db.execute('SELECT * FROM certificates WHERE id = ?', (id,)).fetchone()
    
    if not cert or cert['status'] != 'pending_approval':
        flash('Ijazah tidak valid atau tidak dalam status menunggu persetujuan.', 'danger')
        return redirect(url_for('approval.list_approvals'))
        
    rejection_reason = request.form.get('rejection_reason', '')
    
    db.execute('''
        UPDATE certificates 
        SET status = 'rejected', rejection_reason = ?
        WHERE id = ?
    ''', (rejection_reason, id))
    db.commit()
    
    log_audit(session['user_id'], session['name'], session['role'], 
              'REJECT', 'certificates', f'Rejected certificate ID {id}. Reason: {rejection_reason}', 
              request.remote_addr)
              
    flash('Ijazah telah ditolak.', 'warning')
    return redirect(url_for('approval.list_approvals'))
