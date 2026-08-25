from flask import Blueprint, request, render_template, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from database import get_db, log_audit
from rbac import login_required, role_required, ROLES

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return render_template('users/list.html', users=users)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        
        if existing:
            flash("Email sudah digunakan.", "danger")
            return render_template('users/form.html', mode='add', roles=ROLES)
            
        mfa_enabled = 1 if role in ('staf_tu', 'kepala_sekolah') else 0
        password_hash = generate_password_hash(password)
        
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash, role, mfa_enabled) VALUES (?, ?, ?, ?, ?)",
            (name, email, password_hash, role, mfa_enabled)
        )
        db.commit()
        
        log_audit(
            session.get('user_id'), session.get('name'), session.get('role'),
            'CREATE', 'users', f"Created user {email} with role {role}", request.remote_addr
        )
        
        flash("User berhasil ditambahkan.", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/form.html', mode='add', roles=ROLES)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def edit_user(id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    
    if not user:
        flash("User tidak ditemukan.", "danger")
        return redirect(url_for('users.list_users'))
        
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        existing = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, id)).fetchone()
        if existing:
            flash("Email sudah digunakan oleh user lain.", "danger")
            return render_template('users/form.html', mode='edit', user=user, roles=ROLES)
            
        mfa_enabled = 1 if role in ('staf_tu', 'kepala_sekolah') else 0
        
        if password:
            password_hash = generate_password_hash(password)
            db.execute(
                "UPDATE users SET name = ?, email = ?, password_hash = ?, role = ?, mfa_enabled = ? WHERE id = ?",
                (name, email, password_hash, role, mfa_enabled, id)
            )
        else:
            db.execute(
                "UPDATE users SET name = ?, email = ?, role = ?, mfa_enabled = ? WHERE id = ?",
                (name, email, role, mfa_enabled, id)
            )
        db.commit()
        
        log_audit(
            session.get('user_id'), session.get('name'), session.get('role'),
            'UPDATE', 'users', f"Updated user {email}", request.remote_addr
        )
        
        flash("User berhasil diperbarui.", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/form.html', mode='edit', user=user, roles=ROLES)

@bp.route('/<int:id>/toggle-mfa', methods=['POST'])
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def toggle_mfa(id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    
    if not user:
        flash("User tidak ditemukan.", "danger")
        return redirect(url_for('users.list_users'))
        
    new_status = 0 if user['mfa_enabled'] else 1
    
    if new_status == 0 and user['role'] in ('staf_tu', 'kepala_sekolah'):
        flash("MFA wajib untuk Staf TU dan Kepala Sekolah.", "warning")
        return redirect(url_for('users.list_users'))
        
    db.execute("UPDATE users SET mfa_enabled = ? WHERE id = ?", (new_status, id))
    db.commit()
    
    status_str = "enabled" if new_status else "disabled"
    log_audit(
        session.get('user_id'), session.get('name'), session.get('role'),
        'UPDATE', 'users', f"Toggled MFA to {status_str} for user {user['email']}", request.remote_addr
    )
    
    flash(f"MFA status updated to {status_str} for {user['name']}.", "info")
    return redirect(url_for('users.list_users'))
