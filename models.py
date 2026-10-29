from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(255))
    full_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    section = db.Column(db.String(100))
    role = db.Column(db.String(50))
    is_approved = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name or '',
            'department': self.department or '',
            'section': self.section or '',
            'role': self.role or 'Staff',
            'is_approved': bool(self.is_approved)
        }

class ProjectNew(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(255))
    part_no = db.Column(db.String(100))
    project = db.Column(db.String(255))
    customer = db.Column(db.String(100))
    status = db.Column(db.String(50))
    pic = db.Column(db.String(100))
    i_code = db.Column(db.String(50))
    project_start_date = db.Column(db.String(20))
    project_end_date = db.Column(db.String(20))
    created_at = db.Column(db.String(50))
    updated_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), default='Prod MC')

    documents = db.relationship('ProjectDocument', backref='project', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_documents=False):
        data = {
            'id': self.id,
            'item': self.item or '',
            'part_no': self.part_no or '',
            'project_name': self.project or '',
            'customer': self.customer or '',
            'status': self.status or 'On Progress',
            'pic': self.pic or '',
            'i_code': self.i_code or '',
            'project_start_date': self.project_start_date or '',
            'project_end_date': self.project_end_date or '',
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'department': self.department or 'Prod MC'
        }
        if include_documents:
            data['documents'] = [d.to_dict() for d in self.documents] if self.documents else []
        return data

class DocumentType(db.Model):
    __tablename__ = 'document_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), default='Prod MC')
    is_multiple = db.Column(db.Boolean, default=False)
    default_delegate_id = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department or 'Prod MC',
            'is_multiple': self.is_multiple,
            'default_delegate_id': self.default_delegate_id
        }

class ProjectDocument(db.Model):
    __tablename__ = 'project_documents'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    doc_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    department = db.Column(db.String(100), default='Prod MC')
    delegated_to_id = db.Column(db.String(100))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.String(50))
    uploaded_by = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Empty')

    doc_type = db.relationship('DocumentType')
    revisions = db.relationship('DocumentRevision', backref='project_document', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        delegated_name = self.delegated_to_id
        if self.delegated_to_id:
            u = User.query.get(self.delegated_to_id)
            if u and u.full_name:
                delegated_name = u.full_name

        dept = self.department or (self.doc_type.department if self.doc_type else 'Prod MC') or 'Prod MC'

        return {
            'id': self.id,
            'project_id': self.project_id,
            'doc_type_id': self.doc_type_id,
            'doc_type_name': self.doc_type.name if self.doc_type else None,
            'department': dept,
            'is_multiple': bool(self.doc_type.is_multiple) if self.doc_type else False,
            'delegated_to_id': self.delegated_to_id,
            'delegated_to_name': delegated_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at,
            'uploaded_by': self.uploaded_by,
            'status': self.status or 'Empty',
            'revisions': [r.to_dict() for r in self.revisions] if self.revisions else []
        }

class DocumentRevision(db.Model):
    __tablename__ = 'document_revisions'

    id = db.Column(db.Integer, primary_key=True)
    project_document_id = db.Column(db.Integer, db.ForeignKey('project_documents.id'), nullable=False)
    revision_number = db.Column(db.Integer, default=1)
    batch_number = db.Column(db.Integer, default=1)
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.String(50))
    uploaded_by = db.Column(db.String(100))
    status = db.Column(db.String(20))

    def to_dict(self):
        return {
            'id': self.id,
            'project_document_id': self.project_document_id,
            'revision_number': self.revision_number,
            'batch_number': self.batch_number or 1,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at,
            'timestamp': self.uploaded_at,
            'uploaded_by': self.uploaded_by,
            'status': self.status
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50))
    user_id = db.Column(db.String(50))
    user_name = db.Column(db.String(100))
    action = db.Column(db.String(50))
    details = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'action': self.action,
            'details': self.details
        }

