from flask import Blueprint, request, render_template, session
from database import get_db
from rbac import login_required, role_required

bp = Blueprint('audit', __name__, url_prefix='/audit-logs')

@bp.route('/')
@login_required
@role_required('staf_tu', 'kepala_sekolah')
def list_audit_logs():
    db = get_db()
    
    user = request.args.get('user', '')
    action = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if user:
        query += " AND user_name LIKE ?"
        params.append(f"%{user}%")
        
    if action and action != 'All':
        query += " AND action = ?"
        params.append(action)
        
    if date_from:
        query += " AND date(timestamp) >= ?"
        params.append(date_from)
        
    if date_to:
        query += " AND date(timestamp) <= ?"
        params.append(date_to)
        
    query += " ORDER BY timestamp DESC LIMIT 200"
    
    logs = db.execute(query, params).fetchall()
    
    actions = [
        'LOGIN', 'LOGOUT', 'MFA_VERIFY', 'ACCESS_DENIED', 'CREATE', 
        'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 'SUBMIT', 
        'GRADE_CREATE', 'GRADE_UPDATE', 'CERTIFICATE_CREATE', 'BLOCKCHAIN_RECORD'
    ]
    
    return render_template('audit/list.html', 
                           logs=logs, 
                           actions=actions, 
                           current_user=user, 
                           current_action=action, 
                           current_from=date_from, 
                           current_to=date_to)
