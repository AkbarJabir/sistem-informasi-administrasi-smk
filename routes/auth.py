from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import get_db, log_audit
from rbac import MFA_REQUIRED_ROLES

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['mfa_verified'] = False
            
            log_audit(
                user_id=user['id'],
                user_name=user['name'],
                user_role=user['role'],
                action='login',
                resource='auth',
                detail='User logged in successfully',
                ip_address=request.remote_addr
            )
            
            if user['role'] in MFA_REQUIRED_ROLES:
                return redirect(url_for('auth.mfa_verify'))
            else:
                return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@bp.route('/mfa-verify', methods=['GET', 'POST'])
def mfa_verify():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if otp == '123456':
            session['mfa_verified'] = True
            log_audit(
                user_id=session['user_id'],
                user_name=session['name'],
                user_role=session['role'],
                action='mfa_verify',
                resource='auth',
                detail='MFA verification successful',
                ip_address=request.remote_addr
            )
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid OTP code', 'danger')
            log_audit(
                user_id=session['user_id'],
                user_name=session['name'],
                user_role=session['role'],
                action='mfa_failed',
                resource='auth',
                detail='MFA verification failed',
                ip_address=request.remote_addr
            )
            
    return render_template('mfa.html')

@bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_audit(
            user_id=session.get('user_id'),
            user_name=session.get('name'),
            user_role=session.get('role'),
            action='logout',
            resource='auth',
            detail='User logged out',
            ip_address=request.remote_addr
        )
    session.clear()
    return redirect(url_for('auth.login'))
