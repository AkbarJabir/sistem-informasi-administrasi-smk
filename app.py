"""
Sistem Informasi Administrasi SMK
Main Application Entry Point

Prototype web administrasi SMK dengan:
- Cloud Security Architecture (Zero Trust)
- Blockchain untuk integritas dokumen
- RBAC pada setiap halaman dan endpoint
- MFA simulasi untuk akun administratif
"""

import os
from flask import Flask, redirect, url_for, session, request, jsonify, flash
from database import init_db, seed_data
from rbac import get_sidebar_menu, get_role_display
from blockchain import blockchain

# ── App Initialization ──
app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ── Context Processors ──
@app.context_processor
def inject_globals():
    """Inject sidebar menu and role display into all templates."""
    return {
        'sidebar_menu': get_sidebar_menu(),
        'role_display': get_role_display(session.get('role', ''))
    }


# ── Register Blueprints ──
from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.students import bp as students_bp
from routes.grades import bp as grades_bp
from routes.certificates import bp as certificates_bp
from routes.approval import bp as approval_bp
from routes.verification import bp as verification_bp
from routes.internship import bp as internship_bp
from routes.audit import bp as audit_bp
from routes.users import bp as users_bp
from routes.security import bp as security_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(students_bp)
app.register_blueprint(grades_bp)
app.register_blueprint(certificates_bp)
app.register_blueprint(approval_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(internship_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(users_bp)
app.register_blueprint(security_bp)


# ── Root Route ──
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))


# ── API Endpoint: Grade Update (PRD Section 11.2) ──
@app.route('/api/v1/grades/update', methods=['POST'])
def api_grades_update():
    """API endpoint for grade update. Enforces RBAC at backend level."""
    from database import get_db, log_audit
    from flask import jsonify
    import sqlite3

    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session.get('role') != 'guru':
        log_audit(
            session.get('user_id'), session.get('name', 'Unknown'),
            session.get('role', ''), 'ACCESS_DENIED', '/api/v1/grades/update',
            f'Role "{session.get("role")}" attempted API grade update.',
            request.remote_addr or '127.0.0.1'
        )
        return jsonify({"error": "Forbidden", "message": "You do not have permission to perform this action."}), 403

    if request.is_json:
        data = request.get_json()
        grade_id = data.get('grade_id')
        new_score = data.get('new_score')
    else:
        grade_id = request.form.get('grade_id')
        new_score = request.form.get('new_score')

    if not grade_id or new_score is None:
        return jsonify({"error": "Missing parameters: grade_id and new_score required"}), 400

    try:
        new_score = float(new_score)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid score format"}), 400

    db = get_db()
    grade = db.execute('SELECT * FROM grades WHERE id = ?', (grade_id,)).fetchone()
    if not grade:
        db.close()
        return jsonify({"error": "Grade not found"}), 404

    old_score = grade['score']

    try:
        db.execute('UPDATE grades SET score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                   (new_score, grade_id))
        db.execute('''
            INSERT INTO grade_audit_logs (grade_id, user_id, action, old_value, new_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (grade_id, session['user_id'], 'UPDATE', str(old_score), str(new_score)))
        db.commit()

        log_audit(session['user_id'], session.get('name'), session.get('role'),
                  'GRADE_UPDATE', 'grades',
                  f'Updated grade {grade_id}: {old_score} -> {new_score}',
                  request.remote_addr)

        if request.is_json:
            return jsonify({"success": True, "message": "Grade updated successfully",
                            "old_score": old_score, "new_score": new_score})
        else:
            from flask import flash
            flash('Nilai berhasil diupdate.', 'success')
            return redirect(url_for('grades.list_grades'))
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── Error Handlers ──
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('auth.login'))


@app.errorhandler(413)
def too_large(e):
    from flask import flash
    flash('File terlalu besar. Maksimal 16 MB.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


# ── Initialize ──
if __name__ == '__main__':
    # Initialize database and seed data
    init_db()
    seed_data()

    # Load existing blockchain from database
    blockchain.load_from_db()

    print("=" * 60)
    print("  Sistem Informasi Administrasi SMK")
    print("  Zero Trust & Blockchain Security Prototype")
    print("=" * 60)
    print()
    print("  Server: http://127.0.0.1:5000")
    print()
    print("  Demo Accounts:")
    print("  +--------------------------+-----------+------------------+")
    print("  | Email                    | Password  | Role             |")
    print("  +--------------------------+-----------+------------------+")
    print("  | siswa@smk.sch.id         | siswa123  | Siswa            |")
    print("  | guru@smk.sch.id          | guru123   | Guru             |")
    print("  | tu@smk.sch.id            | tu123     | Staf TU (MFA)    |")
    print("  | kepsek@smk.sch.id        | kepsek123 | Kep. Sekolah(MFA)|")
    print("  | dudi@industry.co.id      | dudi123   | Mitra DUDI       |")
    print("  +--------------------------+-----------+------------------+")
    print()
    print("  MFA Demo OTP: 123456")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
