from flask import Blueprint, jsonify, request
from models import db, DocumentType, ProjectDocument
from routes.audit import log_activity
from datetime import datetime

document_types_bp = Blueprint('document_types', __name__)

@document_types_bp.route('/api/document-types', methods=['GET'])
def get_document_types():
    """Get all document types"""
    try:
        types = DocumentType.query.all()
        return jsonify([type.to_dict() for type in types]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@document_types_bp.route('/api/document-types', methods=['POST'])
def create_document_type():
    """Create a new document type"""
    user_role = request.headers.get('X-User-Role')
    if not user_role or user_role.lower() not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized: Admin role required to create document types'}), 403

    try:
        data = request.get_json()
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400

        existing = DocumentType.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Document type with this name already exists'}), 400

        dept = data.get('department') or 'Prod MC'
        new_type = DocumentType(
            name=data['name'],
            department=dept,
            is_multiple=data.get('is_multiple', False),
            default_delegate_id=data.get('default_delegate_id')
        )
        db.session.add(new_type)
        db.session.flush()

        # Automatically provision this new document type into all existing projects
        from models import ProjectNew
        all_projs = ProjectNew.query.all()
        for p in all_projs:
            p_doc = ProjectDocument(
                project_id=p.id,
                doc_type_id=new_type.id,
                department=dept,
                status='Empty',
                delegated_to_id=new_type.default_delegate_id
            )
            db.session.add(p_doc)
        db.session.commit()

        admin_name = request.headers.get('X-User-Name', 'Admin')
        log_activity(
            request.headers.get('X-User-Role', 'System'),
            admin_name,
            'CREATE_DOC_TYPE',
            f'Created document type: {new_type.name}'
        )

        return jsonify(new_type.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@document_types_bp.route('/api/document-types/<int:type_id>', methods=['PUT'])
def update_document_type(type_id):
    """Update a document type"""
    user_role = request.headers.get('X-User-Role')
    if not user_role or user_role.lower() not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized: Admin role required to update document types'}), 403

    try:
        doc_type = DocumentType.query.get_or_404(type_id)
        data = request.get_json()

        if 'name' in data and data['name'] != doc_type.name:
            existing = DocumentType.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'error': 'Document type with this name already exists'}), 400

        if 'name' in data:
            doc_type.name = data['name']
        if 'department' in data:
            doc_type.department = data['department'] or 'Prod MC'
        if 'is_multiple' in data:
            doc_type.is_multiple = data['is_multiple']
        if 'default_delegate_id' in data:
            old_delegate = doc_type.default_delegate_id
            new_delegate = data['default_delegate_id']
            doc_type.default_delegate_id = new_delegate

            if old_delegate != new_delegate:
                empty_docs = ProjectDocument.query.filter_by(doc_type_id=type_id, status='Empty').all()
                updated_count = 0
                for doc in empty_docs:
                    doc.delegated_to_id = new_delegate
                    updated_count += 1
                print(f'Updated {updated_count} empty documents with new default delegate')

        db.session.commit()

        admin_name = request.headers.get('X-User-Name', 'Admin')
        log_activity(
            request.headers.get('X-User-Role', 'System'),
            admin_name,
            'UPDATE_DOC_TYPE',
            f'Updated document type: {doc_type.name}'
        )

        return jsonify(doc_type.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@document_types_bp.route('/api/document-types/<int:type_id>', methods=['DELETE'])
def delete_document_type(type_id):
    """Delete a document type"""
    user_role = request.headers.get('X-User-Role')
    if not user_role or user_role.lower() not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized: Admin role required to delete document types'}), 403

    try:
        doc_type = DocumentType.query.get_or_404(type_id)
        doc_name = doc_type.name
        db.session.delete(doc_type)
        db.session.commit()

        admin_name = request.headers.get('X-User-Name', 'Admin')
        log_activity(
            request.headers.get('X-User-Role', 'System'),
            admin_name,
            'DELETE_DOC_TYPE',
            f'Deleted document type: {doc_name}'
        )

        return jsonify({'message': 'Document type deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
