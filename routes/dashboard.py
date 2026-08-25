from flask import Blueprint, render_template, session
from database import get_db
from rbac import login_required, mfa_required

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
@mfa_required
def dashboard():
    db = get_db()
    role = session.get('role')
    user_id = session.get('user_id')
    stats = {}

    if role == 'siswa':
        student = db.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchone()
        stats['student'] = student
        if student:
            stats['grade_count'] = db.execute('SELECT COUNT(*) as count FROM grades WHERE student_id = ?', (student['id'],)).fetchone()['count']
            stats['certificate_count'] = db.execute('SELECT COUNT(*) as count FROM certificates WHERE student_id = ?', (student['id'],)).fetchone()['count']
        else:
            stats['grade_count'] = 0
            stats['certificate_count'] = 0

    elif role == 'guru':
        stats['student_count'] = db.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
        stats['grade_count'] = db.execute('SELECT COUNT(*) as count FROM grades WHERE teacher_id = ?', (user_id,)).fetchone()['count']

    elif role == 'staf_tu':
        stats['student_count'] = db.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
        stats['cert_count'] = db.execute('SELECT COUNT(*) as count FROM certificates').fetchone()['count']
        stats['pending_count'] = db.execute('SELECT COUNT(*) as count FROM certificates WHERE status = ?', ('pending_approval',)).fetchone()['count']
        stats['user_count'] = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']

    elif role == 'kepala_sekolah':
        stats['pending_count'] = db.execute('SELECT COUNT(*) as count FROM certificates WHERE status = ?', ('pending_approval',)).fetchone()['count']
        stats['approved_count'] = db.execute('SELECT COUNT(*) as count FROM certificates WHERE status = ?', ('approved',)).fetchone()['count']
        stats['student_count'] = db.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']

    elif role == 'mitra_dudi':
        stats['internship_count'] = db.execute('SELECT COUNT(*) as count FROM internship_certificates').fetchone()['count']

    db.close()
    return render_template('dashboard.html', role=role, stats=stats)
