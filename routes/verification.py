from flask import Blueprint, request, render_template, session, flash, redirect
from blockchain import compute_sha256, smart_contract
from database import get_db

bp = Blueprint('verification', __name__, url_prefix='/verify')

@bp.route('/', methods=['GET', 'POST'])
def verify_index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file_bytes = file.read()
        computed_hash = compute_sha256(file_bytes)
        
        result = smart_contract.verify_certificate(computed_hash)
        
        # also check in database
        db = get_db()
        db_cert = db.execute("SELECT * FROM certificates WHERE document_hash = ?", (computed_hash,)).fetchone()
        if not db_cert:
            db_cert = db.execute("SELECT * FROM internship_certificates WHERE document_hash = ?", (computed_hash,)).fetchone()
            
        return render_template('verify.html', uploaded_hash=computed_hash, result=result, db_cert=db_cert)
        
    return render_template('verify.html')
