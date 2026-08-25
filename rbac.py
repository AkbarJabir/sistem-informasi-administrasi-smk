"""
RBAC (Role-Based Access Control) module for Sistem Informasi Administrasi SMK.
Implements Zero Trust principle: every request is verified for identity, role, MFA, and authorization.
"""

from functools import wraps
from flask import session, redirect, url_for, render_template, request, abort
from database import log_audit


# ── Role Definitions ──
ROLES = {
    'siswa': 'Siswa',
    'guru': 'Guru',
    'staf_tu': 'Staf TU',
    'kepala_sekolah': 'Kepala Sekolah',
    'mitra_dudi': 'Mitra DUDI'
}

# Roles that require MFA
MFA_REQUIRED_ROLES = ['staf_tu', 'kepala_sekolah']

# ── Page access matrix (role → allowed pages) ──
PAGE_ACCESS = {
    'siswa': ['dashboard', 'grades_view', 'profile', 'verify'],
    'guru': ['dashboard', 'students_view', 'grades_view', 'grades_edit', 'grades_add', 'grades_history', 'verify'],
    'staf_tu': ['dashboard', 'students_view', 'students_edit', 'students_add',
                'grades_view', 'certificates_view', 'certificates_create',
                'certificates_upload', 'certificates_submit',
                'internship_view', 'internship_create',
                'audit_logs', 'users_view', 'users_edit', 'verify',
                'cloud_architecture', 'security_dashboard'],
    'kepala_sekolah': ['dashboard', 'students_view', 'grades_view',
                       'certificates_view', 'approval_view', 'approval_action',
                       'audit_logs', 'users_view', 'users_edit', 'verify',
                       'cloud_architecture', 'security_dashboard'],
    'mitra_dudi': ['dashboard', 'verify', 'internship_view']
}

# ── Sidebar menu per role ──
SIDEBAR_MENUS = {
    'siswa': [
        {'icon': 'bi-speedometer2', 'label': 'Dashboard', 'url': '/dashboard'},
        {'icon': 'bi-journal-text', 'label': 'Nilai Saya', 'url': '/grades'},
        {'icon': 'bi-patch-check', 'label': 'Verifikasi Dokumen', 'url': '/verify'},
    ],
    'guru': [
        {'icon': 'bi-speedometer2', 'label': 'Dashboard', 'url': '/dashboard'},
        {'icon': 'bi-people', 'label': 'Data Siswa', 'url': '/students'},
        {'icon': 'bi-journal-text', 'label': 'Manajemen Nilai', 'url': '/grades'},
        {'icon': 'bi-patch-check', 'label': 'Verifikasi Dokumen', 'url': '/verify'},
    ],
    'staf_tu': [
        {'icon': 'bi-speedometer2', 'label': 'Dashboard', 'url': '/dashboard'},
        {'icon': 'bi-people', 'label': 'Data Siswa', 'url': '/students'},
        {'icon': 'bi-journal-text', 'label': 'Data Nilai', 'url': '/grades'},
        {'icon': 'bi-file-earmark-medical', 'label': 'Manajemen Ijazah', 'url': '/certificates'},
        {'icon': 'bi-building', 'label': 'Sertifikat PKL', 'url': '/internship'},
        {'icon': 'bi-patch-check', 'label': 'Verifikasi Dokumen', 'url': '/verify'},
        {'icon': 'bi-shield-shaded', 'label': 'Security Dashboard', 'url': '/security-dashboard'},
        {'icon': 'bi-diagram-3', 'label': 'Cloud Architecture', 'url': '/cloud-architecture'},
        {'icon': 'bi-clock-history', 'label': 'Audit Log', 'url': '/audit-logs'},
        {'icon': 'bi-person-gear', 'label': 'User Management', 'url': '/users'},
    ],
    'kepala_sekolah': [
        {'icon': 'bi-speedometer2', 'label': 'Dashboard', 'url': '/dashboard'},
        {'icon': 'bi-people', 'label': 'Data Siswa', 'url': '/students'},
        {'icon': 'bi-journal-text', 'label': 'Data Nilai', 'url': '/grades'},
        {'icon': 'bi-file-earmark-medical', 'label': 'Manajemen Ijazah', 'url': '/certificates'},
        {'icon': 'bi-clipboard-check', 'label': 'Persetujuan Ijazah', 'url': '/approval'},
        {'icon': 'bi-patch-check', 'label': 'Verifikasi Dokumen', 'url': '/verify'},
        {'icon': 'bi-shield-shaded', 'label': 'Security Dashboard', 'url': '/security-dashboard'},
        {'icon': 'bi-diagram-3', 'label': 'Cloud Architecture', 'url': '/cloud-architecture'},
        {'icon': 'bi-clock-history', 'label': 'Audit Log', 'url': '/audit-logs'},
        {'icon': 'bi-person-gear', 'label': 'User Management', 'url': '/users'},
    ],
    'mitra_dudi': [
        {'icon': 'bi-speedometer2', 'label': 'Dashboard', 'url': '/dashboard'},
        {'icon': 'bi-building', 'label': 'Sertifikat PKL', 'url': '/internship'},
        {'icon': 'bi-patch-check', 'label': 'Verifikasi Dokumen', 'url': '/verify'},
    ]
}


def login_required(f):
    """Decorator: require authenticated session (Zero Trust identity check)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def mfa_required(f):
    """Decorator: require MFA verification for administrative roles."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        role = session.get('role', '')
        if role in MFA_REQUIRED_ROLES and not session.get('mfa_verified', False):
            return redirect(url_for('auth.mfa_verify'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Decorator: require specific role(s). Returns 403 if not authorized."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            user_role = session.get('role', '')
            # MFA check for admin roles
            if user_role in MFA_REQUIRED_ROLES and not session.get('mfa_verified', False):
                return redirect(url_for('auth.mfa_verify'))
            if user_role not in roles:
                # Log unauthorized access attempt
                log_audit(
                    session.get('user_id'),
                    session.get('name', 'Unknown'),
                    user_role,
                    'ACCESS_DENIED',
                    request.path,
                    f'Role "{user_role}" attempted to access restricted resource.',
                    request.remote_addr or '127.0.0.1'
                )
                return render_template('403.html', role=ROLES.get(user_role, user_role)), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_sidebar_menu():
    """Get sidebar menu items for the current user's role."""
    role = session.get('role', '')
    return SIDEBAR_MENUS.get(role, [])


def get_role_display(role_key):
    """Get display name for a role key."""
    return ROLES.get(role_key, role_key)
