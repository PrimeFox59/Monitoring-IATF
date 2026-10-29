from flask import Blueprint, jsonify, request, send_file, current_app
from werkzeug.utils import secure_filename
from models import db, ProjectNew, ProjectDocument, DocumentType, User, DocumentRevision
from routes.audit import log_activity
from datetime import datetime
import os
import re
import json

import mimetypes

documents_bp = Blueprint('documents', __name__)

DANGEROUS_EXTENSIONS = {'exe', 'com', 'bat', 'cmd', 'vbs', 'msi', 'scr', 'pif'}

def allowed_file(filename, is_multiple=False):
    if not filename or not filename.strip():
        return False
    # Pada case multiple file: support segala bentuk file (tanpa batasan ekstensi)
    if is_multiple:
        return True
    # Untuk file tunggal: dukung seluruh format non-executable
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        return ext not in DANGEROUS_EXTENSIONS
    return True

def get_absolute_path(relative_path):
    if not relative_path:
        return ''
    if os.path.exists(relative_path):
        return relative_path

    upload_folder = current_app.config.get('UPLOAD_FOLDER', '')

    norm = relative_path.replace('\\', '/')
    while norm.lower().startswith('uploads/'):
        norm = norm[8:]
    if 'uploads/' in norm.lower():
        parts = norm.split('uploads/')
        norm = parts[-1]

    rel = norm.lstrip('/').replace('/', os.sep)
    candidate = os.path.join(upload_folder, rel)
    if os.path.exists(candidate):
        return candidate

    base = os.path.basename(relative_path)
    candidate = os.path.join(upload_folder, base)
    if os.path.exists(candidate):
        return candidate

    master_sample = os.path.join(upload_folder, 'master_sample.pdf')
    if os.path.exists(master_sample):
        return master_sample

    return os.path.join(upload_folder, rel)

def calculate_vba_score(filename, project_name, part_no, item_name):
    """
    Refined VBA-inspired matching logic.
    - Tokenizes words intelligently (ignoring punctuation).
    - Gives weight to Part Number matches (high priority).
    - Uses unique word count for normalizing.
    """
    clean_filename = os.path.splitext(filename)[0].upper()
    file_tokens = set(re.findall(r'[A-Z0-9]+', clean_filename))
    if not file_tokens:
        return 0

    score = 0
    weights_total = 0

    if part_no:
        clean_part = part_no.upper()
        part_tokens = set(re.findall(r'[A-Z0-9]+', clean_part))
        if part_tokens:
            weights_total += 50
            matches = part_tokens.intersection(file_tokens)
            if clean_part in clean_filename:
                score += 50
            elif matches:
                score += 50 * (len(matches) / len(part_tokens))

    if project_name:
        clean_proj = project_name.upper()
        proj_tokens = set(re.findall(r'[A-Z0-9]+', clean_proj))
        if proj_tokens:
            weights_total += 30
            matches = proj_tokens.intersection(file_tokens)
            if clean_proj in clean_filename:
                score += 30
            elif matches:
                score += 30 * (len(matches) / len(proj_tokens))

    if item_name:
        clean_item = item_name.upper()
        item_tokens = set(re.findall(r'[A-Z0-9]+', clean_item))
        if item_tokens:
            weights_total += 20
            matches = item_tokens.intersection(file_tokens)
            if clean_item in clean_filename:
                score += 20
            elif matches:
                score += 20 * (len(matches) / len(item_tokens))

    if weights_total == 0:
        return 0

    normalized_score = int((score / weights_total) * 100)
    return min(100, max(0, normalized_score))

@documents_bp.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """Upload one or more document files (supports multiple file upload)"""
    try:
        user_role = request.headers.get('X-User-Role', 'Staff')
        user_name = request.headers.get('X-User-Name', 'Guest')

        # Support both 'files' (multiple) and 'file' (single)
        files = request.files.getlist('files') or request.files.getlist('file')
        valid_files = [f for f in files if f and f.filename != '']

        if not valid_files:
            return jsonify({'error': 'No file uploaded'}), 400

        project_id = request.form.get('project_id', type=int)
        doc_type_id = request.form.get('doc_type_id', type=int)
        document_id = request.form.get('document_id', type=int)

        if document_id:
            document = ProjectDocument.query.get_or_404(document_id)
        elif project_id and doc_type_id:
            document = ProjectDocument.query.filter_by(project_id=project_id, doc_type_id=doc_type_id).first()
            if not document:
                document = ProjectDocument(project_id=project_id, doc_type_id=doc_type_id)
                db.session.add(document)
                db.session.flush()
        else:
            return jsonify({'error': 'Missing document identifiers'}), 400

        project = ProjectNew.query.get(document.project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        doc_type = DocumentType.query.get(document.doc_type_id)
        doc_type_name = doc_type.name if doc_type else 'Document'
        is_multiple = bool(doc_type.is_multiple) if doc_type else (len(valid_files) > 1)

        # Check allowed file types (support all formats if is_multiple)
        for f in valid_files:
            if not allowed_file(f.filename, is_multiple=is_multiple):
                return jsonify({'error': f'File type not allowed: {f.filename}'}), 400

        # Permission check
        if user_role != 'Admin' and document.delegated_to_id and document.delegated_to_id != user_name:
            user = User.query.get(document.delegated_to_id)
            if not user or user.full_name != user_name:
                return jsonify({'error': 'Unauthorized to upload this document'}), 403

        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        current_rev_count = len(document.revisions)
        max_batch = db.session.query(db.func.max(DocumentRevision.batch_number)).filter_by(project_document_id=document.id).scalar() or 0
        current_batch_number = max_batch + 1
        uploaded_revisions = []
        last_saved_filename = None
        now_str = datetime.now().isoformat()

        for idx, file in enumerate(valid_files):
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            orig_filename = secure_filename(file.filename)
            if not orig_filename:
                orig_filename = file.filename.replace(' ', '_').replace('/', '_').replace('\\', '_')
            suffix = f"_{idx+1}" if len(valid_files) > 1 else ""
            saved_filename = f"{document.id}_{timestamp_str}{suffix}_{orig_filename}"
            full_dest_path = os.path.join(upload_folder, saved_filename)
            file.save(full_dest_path)

            new_rev_number = current_rev_count + idx + 1
            new_revision = DocumentRevision(
                project_document_id=document.id,
                revision_number=new_rev_number,
                batch_number=current_batch_number,
                file_path=saved_filename,
                uploaded_at=now_str,
                uploaded_by=user_name,
                status='Uploaded'
            )
            db.session.add(new_revision)
            uploaded_revisions.append(new_revision)
            last_saved_filename = saved_filename

        # Update document main record
        document.file_path = last_saved_filename
        document.status = 'Uploaded'
        document.uploaded_at = now_str
        document.uploaded_by = user_name

        project.updated_at = now_str
        db.session.commit()

        project_info = f"Project: {project.project or 'Unknown'} | Item: {project.item or '-'} | Part No: {project.part_no or '-'} | Customer: {project.customer or '-'}"
        log_activity(
            user_role,
            user_name,
            'UPLOAD_DOCUMENT',
            f"Uploaded {len(valid_files)} file(s) for {doc_type_name} for {project_info}"
        )

        return jsonify({
            'message': f'{len(valid_files)} file(s) uploaded successfully',
            'document': document.to_dict(),
            'revision': uploaded_revisions[-1].to_dict() if uploaded_revisions else None,
            'revisions': [r.to_dict() for r in uploaded_revisions]
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/download/<int:document_id>', methods=['GET'])
@documents_bp.route('/api/documents/<int:document_id>/download', methods=['GET'])
def download_document(document_id):
    """Download the latest document file"""
    try:
        document = ProjectDocument.query.get_or_404(document_id)
        if not document.file_path:
            return jsonify({'error': 'No file uploaded for this document'}), 404

        abs_path = get_absolute_path(document.file_path)
        if not os.path.exists(abs_path):
            return jsonify({'error': 'File not found on server'}), 404

        user_name = request.args.get('user_name') or request.headers.get('X-User-Name', 'Guest')
        user_role = request.args.get('user_role') or request.headers.get('X-User-Role', 'System')
        project = document.project
        doc_type = document.doc_type

        project_info = f"Project: {project.project if project else 'Unknown'} | Item: {project.item if project else '-'} | Part No: {project.part_no if project else '-'} | Customer: {project.customer if project else '-'}"
        try:
            log_activity(
                user_role,
                user_name,
                'DOWNLOAD_DOCUMENT',
                f"Downloaded {doc_type.name if doc_type else 'Document'} from {project_info}"
            )
        except Exception:
            pass

        raw_name = os.path.basename(document.file_path) if document.file_path else os.path.basename(abs_path)
        clean_name = re.sub(r'^\d+_\d{8}_\d{6}(?:_\d+)?_', '', raw_name)
        if not clean_name.lower().endswith('.pdf'):
            clean_name += '.pdf'
        return send_file(abs_path, as_attachment=True, download_name=clean_name)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/view/<int:document_id>', methods=['GET'])
@documents_bp.route('/api/documents/<int:document_id>/view', methods=['GET'])
def view_document(document_id):
    """View a document in the browser"""
    try:
        document = ProjectDocument.query.get_or_404(document_id)
        if not document.file_path:
            return jsonify({'error': 'No file uploaded for this document'}), 404

        abs_path = get_absolute_path(document.file_path)
        if not os.path.exists(abs_path):
            return jsonify({'error': 'File not found on server'}), 404

        ext = os.path.splitext(abs_path)[1].lower()
        if ext == '.png':
            mimetype = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mimetype = 'image/jpeg'
        elif ext == '.pdf':
            mimetype = 'application/pdf'
        elif ext in ('.txt', '.log', '.gcode', '.nc', '.tap'):
            mimetype = 'text/plain'
        elif ext == '.csv':
            mimetype = 'text/csv'
        elif ext == '.json':
            mimetype = 'application/json'
        elif ext == '.svg':
            mimetype = 'image/svg+xml'
        elif ext == '.webp':
            mimetype = 'image/webp'
        elif ext == '.mp4':
            mimetype = 'video/mp4'
        else:
            guessed, _ = mimetypes.guess_type(abs_path)
            mimetype = guessed or 'application/octet-stream'

        user_name = request.args.get('user_name') or request.headers.get('X-User-Name', 'Guest')
        user_role = request.args.get('user_role') or request.headers.get('X-User-Role', 'System')
        project = document.project
        doc_type = document.doc_type
        project_info = f"Project: {project.project if project else 'Unknown'} | Item: {project.item if project else '-'} | Part No: {project.part_no if project else '-'} | Customer: {project.customer if project else '-'}"

        try:
            log_activity(
                user_role,
                user_name,
                'VIEW_DOCUMENT',
                f"Viewed {doc_type.name if doc_type else 'Document'} in {project_info}"
            )
        except Exception:
            pass

        raw_name = os.path.basename(document.file_path) if document.file_path else os.path.basename(abs_path)
        clean_name = re.sub(r'^\d+_\d{8}_\d{6}(?:_\d+)?_', '', raw_name)
        if not clean_name.lower().endswith('.pdf'):
            clean_name += '.pdf'
        return send_file(abs_path, mimetype=mimetype, as_attachment=False, download_name=clean_name)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/revisions/download/<int:revision_id>', methods=['GET'])
@documents_bp.route('/api/documents/revisions/<int:revision_id>/download', methods=['GET'])
def download_revision(revision_id):
    """Download a specific document revision"""
    try:
        revision = DocumentRevision.query.get_or_404(revision_id)
        abs_path = get_absolute_path(revision.file_path)

        if not os.path.exists(abs_path):
            return jsonify({'error': 'File not found on server'}), 404

        user_name = request.args.get('user_name') or request.headers.get('X-User-Name', 'Guest')
        user_role = request.args.get('user_role') or request.headers.get('X-User-Role', 'System')
        project_doc = revision.project_document
        project = project_doc.project if project_doc else None
        doc_type = project_doc.doc_type if project_doc else None

        project_info = f"Project: {project.project if project else 'Unknown'} | Item: {project.item if project else '-'} | Part No: {project.part_no if project else '-'} | Customer: {project.customer if project else '-'}"
        try:
            log_activity(
                user_role,
                user_name,
                'DOWNLOAD_REVISION',
                f"Downloaded revision {revision.revision_number} of {doc_type.name if doc_type else 'Document'} from {project_info}"
            )
        except Exception:
            pass

        raw_name = os.path.basename(revision.file_path) if revision.file_path else os.path.basename(abs_path)
        clean_name = re.sub(r'^\d+_\d{8}_\d{6}(?:_\d+)?_', '', raw_name)
        if not clean_name.lower().endswith('.pdf'):
            clean_name += '.pdf'
        return send_file(abs_path, as_attachment=True, download_name=clean_name)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/revisions/view/<int:revision_id>', methods=['GET'])
@documents_bp.route('/api/documents/revisions/<int:revision_id>/view', methods=['GET'])
def view_revision(revision_id):
    """View a document revision in the browser"""
    try:
        revision = DocumentRevision.query.get_or_404(revision_id)
        abs_path = get_absolute_path(revision.file_path)

        if not os.path.exists(abs_path):
            return jsonify({'error': 'File not found on server'}), 404

        ext = os.path.splitext(abs_path)[1].lower()
        if ext == '.png':
            mimetype = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mimetype = 'image/jpeg'
        elif ext == '.pdf':
            mimetype = 'application/pdf'
        elif ext in ('.txt', '.log', '.gcode', '.nc', '.tap'):
            mimetype = 'text/plain'
        elif ext == '.csv':
            mimetype = 'text/csv'
        elif ext == '.json':
            mimetype = 'application/json'
        elif ext == '.svg':
            mimetype = 'image/svg+xml'
        elif ext == '.webp':
            mimetype = 'image/webp'
        elif ext == '.mp4':
            mimetype = 'video/mp4'
        else:
            guessed, _ = mimetypes.guess_type(abs_path)
            mimetype = guessed or 'application/octet-stream'

        user_name = request.args.get('user_name') or request.headers.get('X-User-Name', 'Guest')
        user_role = request.args.get('user_role') or request.headers.get('X-User-Role', 'System')
        project_doc = revision.project_document
        project = project_doc.project if project_doc else None
        doc_type = project_doc.doc_type if project_doc else None

        project_info = f"Project: {project.project if project else 'Unknown'} | Item: {project.item if project else '-'} | Part No: {project.part_no if project else '-'} | Customer: {project.customer if project else '-'}"
        try:
            log_activity(
                user_role,
                user_name,
                'VIEW_DOCUMENT',
                f"Viewed revision {revision.revision_number} of {doc_type.name if doc_type else 'Document'} in {project_info}"
            )
        except Exception:
            pass

        raw_name = os.path.basename(revision.file_path) if revision.file_path else os.path.basename(abs_path)
        clean_name = re.sub(r'^\d+_\d{8}_\d{6}(?:_\d+)?_', '', raw_name)
        if not clean_name.lower().endswith('.pdf'):
            clean_name += '.pdf'
        return send_file(abs_path, mimetype=mimetype, as_attachment=False, download_name=clean_name)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/revisions/<int:revision_id>', methods=['DELETE'])
def delete_revision(revision_id):
    """Delete a specific document revision and re-number subsequent ones"""
    user_role = request.headers.get('X-User-Role')
    user_name = request.headers.get('X-User-Name', 'Guest')
    if not user_role or user_role.lower() not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized: Admin role required'}), 403

    try:
        revision = DocumentRevision.query.get_or_404(revision_id)
        doc_id = revision.project_document_id
        deleted_rev_num = revision.revision_number
        file_to_delete = get_absolute_path(revision.file_path)

        db.session.delete(revision)

        subsequent_revisions = DocumentRevision.query.filter(
            DocumentRevision.project_document_id == doc_id,
            DocumentRevision.revision_number > deleted_rev_num
        ).all()

        for rev in subsequent_revisions:
            rev.revision_number -= 1

        if file_to_delete and os.path.exists(file_to_delete):
            try:
                os.remove(file_to_delete)
            except Exception:
                pass

        # Update latest revision pointer on project document
        remaining_revs = DocumentRevision.query.filter_by(
            project_document_id=doc_id
        ).order_by(DocumentRevision.revision_number.desc()).all()

        doc = ProjectDocument.query.get(doc_id)
        if doc:
            if remaining_revs:
                latest = remaining_revs[0]
                doc.file_path = latest.file_path
                doc.uploaded_at = latest.uploaded_at
                doc.uploaded_by = latest.uploaded_by
                doc.status = latest.status
            else:
                doc.file_path = None
                doc.uploaded_at = None
                doc.uploaded_by = None
                doc.status = 'Empty'

        db.session.commit()

        log_activity(
            user_role,
            user_name,
            'DELETE_REVISION',
            f"Deleted revision {deleted_rev_num} of document ID {doc_id}"
        )

        return jsonify({'message': 'Revision deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/<int:document_id>/history', methods=['GET'])
def get_document_history(document_id):
    """Get revision history for a document"""
    try:
        document = ProjectDocument.query.get_or_404(document_id)
        revisions = DocumentRevision.query.filter_by(
            project_document_id=document_id
        ).order_by(DocumentRevision.revision_number.desc()).all()

        return jsonify([r.to_dict() for r in revisions]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/recent', methods=['GET'])
def get_recent_documents():
    """Get list of recently uploaded documents with project metadata"""
    try:
        docs = ProjectDocument.query.filter(
            ProjectDocument.status == 'Uploaded',
            ProjectDocument.file_path != None
        ).order_by(ProjectDocument.uploaded_at.desc()).limit(100).all()

        result = []
        for d in docs:
            project = d.project
            result.append({
                'id': d.id,
                'project_id': d.project_id,
                'project_name': project.project if project else '',
                'department': project.department if (project and project.department) else 'Prod MC',
                'customer': project.customer if project else '',
                'item': project.item if project else '',
                'part_no': project.part_no if project else '',
                'doc_type_name': d.doc_type.name if d.doc_type else '',
                'file_path': d.file_path,
                'uploaded_at': d.uploaded_at,
                'uploaded_by': d.uploaded_by,
                'status': d.status
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document and its revisions"""
    user_role = request.headers.get('X-User-Role')
    user_name = request.headers.get('X-User-Name', 'Guest')
    if not user_role or user_role.lower() not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized: Admin role required'}), 403

    try:
        document = ProjectDocument.query.get_or_404(document_id)

        for rev in document.revisions:
            abs_path = get_absolute_path(rev.file_path)
            if abs_path and os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

        if document.file_path:
            abs_path = get_absolute_path(document.file_path)
            if abs_path and os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

        for rev in list(document.revisions):
            db.session.delete(rev)

        document.file_path = None
        document.status = 'Empty'
        document.uploaded_at = None
        document.uploaded_by = None

        db.session.commit()

        project = document.project
        doc_type = document.doc_type
        project_info = f"Project: {project.project if project else 'Unknown'} | Item: {project.item if project else '-'} | Part No: {project.part_no if project else '-'} | Customer: {project.customer if project else '-'}"

        log_activity(
            user_role,
            user_name,
            'DELETE_DOCUMENT',
            f"Deleted {doc_type.name if doc_type else 'Document'} from {project_info}"
        )

        return jsonify({'message': 'Document deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/bulk-analyze', methods=['POST'])
def bulk_analyze():
    """Analyze filenames and return proposed project/doc type matches"""
    try:
        data = request.get_json(silent=True) or request.json or {}
        filenames = data.get('filenames', [])

        all_projects = ProjectNew.query.all()
        all_doc_types = DocumentType.query.all()

        results = []
        for filename in filenames:
            best_project = None
            best_doc_type = None
            best_score = 0

            # 1. Match Doc Type
            upper_fn = filename.upper()
            for dtype in all_doc_types:
                if dtype.name.upper() in upper_fn:
                    best_doc_type = dtype
                    break

            # 2. Match Project with VBA scoring
            for proj in all_projects:
                score = calculate_vba_score(filename, proj.project, proj.part_no, proj.item)
                if score > best_score:
                    best_score = score
                    best_project = proj

            results.append({
                'filename': filename,
                'matched_project_id': best_project.id if best_project and best_score >= 30 else None,
                'matched_project_name': best_project.project if best_project and best_score >= 30 else None,
                'matched_doc_type_id': best_doc_type.id if best_doc_type else None,
                'matched_doc_type_name': best_doc_type.name if best_doc_type else None,
                'confidence_score': best_score
            })

        return jsonify(results), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/api/documents/bulk-upload', methods=['POST'])
def bulk_upload():
    """Bulk upload files with custom or smart project/document matching"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    files = request.files.getlist('files')
    mappings_str = request.form.get('mappings')
    mappings = json.loads(mappings_str) if mappings_str else []

    user_role = request.headers.get('X-User-Role', 'Staff')
    user_name = request.headers.get('X-User-Name', 'Guest')
    upload_folder = current_app.config['UPLOAD_FOLDER']

    uploaded_count = 0
    errors = []

    for file in files:
        if not file.filename:
            continue

        # Find mapping
        mapping = next((m for m in mappings if m.get('filename') == file.filename), None)
        if not mapping:
            continue

        project_id = mapping.get('project_id')
        doc_type_id = mapping.get('doc_type_id')

        if not project_id or not doc_type_id:
            errors.append(f"Incomplete mapping for {file.filename}")
            continue

        dt = DocumentType.query.get(doc_type_id)
        is_mult = bool(dt.is_multiple) if dt else False

        if not allowed_file(file.filename, is_multiple=is_mult):
            errors.append(f"Invalid file: {file.filename}")
            continue

        try:
            document = ProjectDocument.query.filter_by(
                project_id=project_id,
                doc_type_id=doc_type_id
            ).first()

            if not document:
                document = ProjectDocument(project_id=project_id, doc_type_id=doc_type_id)
                db.session.add(document)
                db.session.flush()

            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            orig_filename = secure_filename(file.filename)
            if not orig_filename:
                orig_filename = file.filename.replace(' ', '_').replace('/', '_').replace('\\', '_')
            saved_filename = f"{document.id}_{timestamp_str}_{orig_filename}"
            full_dest = os.path.join(upload_folder, saved_filename)
            file.save(full_dest)

            current_rev_count = len(document.revisions)
            max_batch = db.session.query(db.func.max(DocumentRevision.batch_number)).filter_by(project_document_id=document.id).scalar() or 0
            new_rev = DocumentRevision(
                project_document_id=document.id,
                revision_number=current_rev_count + 1,
                batch_number=max_batch + 1,
                file_path=saved_filename,
                uploaded_at=datetime.now().isoformat(),
                uploaded_by=user_name,
                status='Uploaded'
            )
            db.session.add(new_rev)

            document.file_path = saved_filename
            document.status = 'Uploaded'
            document.uploaded_at = datetime.now().isoformat()
            document.uploaded_by = user_name

            uploaded_count += 1

        except Exception as err:
            errors.append(f"Failed to process {file.filename}: {str(err)}")

    try:
        db.session.commit()
        return jsonify({
            'message': f'Successfully uploaded {uploaded_count} documents',
            'uploaded_count': uploaded_count,
            'errors': errors
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


