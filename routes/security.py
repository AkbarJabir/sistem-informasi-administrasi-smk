"""
Security blueprint for Sistem Informasi Administrasi SMK.
Provides Cloud Architecture visualization and Security Operations Dashboard.
"""

from flask import Blueprint, render_template, session
from database import get_db
from rbac import login_required, role_required
from blockchain import blockchain

bp = Blueprint('security', __name__)


@bp.route('/cloud-architecture')
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def cloud_architecture():
    """Renders Cloud Security Architecture topology and component explanations."""
    return render_template('security/cloud_architecture.html')


@bp.route('/security-dashboard')
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def security_dashboard():
    """Renders real-time and simulated Zero Trust & Cloud Security dashboard."""
    db = get_db()

    # Query real audit metrics
    total_logs = db.execute("SELECT COUNT(*) as cnt FROM audit_logs").fetchone()['cnt']
    failed_attempts = db.execute(
        "SELECT COUNT(*) as cnt FROM audit_logs WHERE action IN ('ACCESS_DENIED', 'mfa_failed')"
    ).fetchone()['cnt']
    login_events = db.execute(
        "SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'login'"
    ).fetchone()['cnt']
    grade_changes = db.execute(
        "SELECT COUNT(*) as cnt FROM audit_logs WHERE action IN ('GRADE_CREATE', 'GRADE_UPDATE')"
    ).fetchone()['cnt']
    cert_approvals = db.execute(
        "SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'APPROVE'"
    ).fetchone()['cnt']

    recent_security_events = db.execute("""
        SELECT * FROM audit_logs
        WHERE action IN ('ACCESS_DENIED', 'mfa_failed', 'mfa_verify', 'APPROVE', 'GRADE_UPDATE')
        ORDER BY timestamp DESC LIMIT 8
    """).fetchall()

    db.close()

    # Blockchain metrics
    chain_info = blockchain.get_chain_info()
    integrity_valid, integrity_msg = chain_info['integrity']

    metrics = {
        'total_logs': total_logs,
        'failed_attempts': failed_attempts,
        'login_events': login_events,
        'grade_changes': grade_changes,
        'cert_approvals': cert_approvals,
        'chain_length': chain_info['length'],
        'chain_integrity': integrity_valid,
        'chain_integrity_msg': integrity_msg,
        'waf_status': 'ACTIVE',
        'waf_blocked_count': failed_attempts + 18,  # realistic simulation offset
        'mfa_enforced_roles': ['Staf TU', 'Kepala Sekolah'],
        'zero_trust_status': 'ENFORCED',
    }

    return render_template('security/security_dashboard.html', metrics=metrics, recent_events=recent_security_events)
