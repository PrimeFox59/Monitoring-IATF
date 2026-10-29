from flask import Flask, jsonify, send_from_directory, request
from config import Config
from models import db
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def create_app():
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        static_folder = resource_path('dist')
    else:
        static_folder = resource_path('../frontend/dist')
        if not os.path.exists(static_folder):
            static_folder = resource_path('dist')

    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    app.config.from_object(Config)

    if is_frozen:
        exe_dir = os.path.dirname(sys.executable)
        app.config['BASE_DIR'] = exe_dir
        app.config['UPLOAD_FOLDER'] = os.path.join(exe_dir, 'uploads')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(exe_dir, "projects.db")}'
    else:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        app.config['BASE_DIR'] = base_dir
        parent_db = os.path.join(os.path.dirname(base_dir), 'projects.db')
        if os.path.exists(parent_db):
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{parent_db}'
            app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(base_dir), 'uploads')
        else:
            local_db = os.path.join(base_dir, 'projects.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{local_db}'
            app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
        except Exception as e:
            print(f"Error setting SQLite pragma: {e}")
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization', 'X-User-Role', 'X-User-Name']
    )

    from routes.projects import projects_bp
    from routes.documents import documents_bp
    from routes.document_types import document_types_bp
    from routes.users import users_bp
    from routes.audit import audit_bp

    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(document_types_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(audit_bp)

    with app.app_context():
        db.create_all()

        from models import DocumentType
        if DocumentType.query.count() == 0:
            print('Seeding default document types...')
            DEFAULT_DOC_COLUMNS = [
                'DRAWING', 'PIS', 'F DIM', 'FMEA', 'QCPC', 'PAR. PROCESS', 'IK LV.3',
                'ISIR', 'DATA SHEET', 'CAP. ANALAYST', 'LIST MEASURING INST.',
                'MSA', 'SPC / Pp PpK / Cp CpK', 'POKAYOKE', 'DWG JIG', 'REPORT TRIAL'
            ]
            MULTIPLE_FILE_DOCS = [
                'ISIR', 'DATA SHEET', 'CAP. ANALAYST', 'LIST MEASURING INST.',
                'MSA', 'SPC / Pp PpK / Cp CpK', 'POKAYOKE', 'DWG JIG', 'REPORT TRIAL'
            ]

            for doc_name in DEFAULT_DOC_COLUMNS:
                is_mult = doc_name in MULTIPLE_FILE_DOCS
                dtype = DocumentType(name=doc_name, is_multiple=is_mult)
                db.session.add(dtype)

            db.session.commit()
            print('Seeding complete.')
        from models import User
        if User.query.count() == 0:
            print('Seeding default admin user...')
            admin = User(
                id='admin',
                password='password',
                full_name='GALIH PRIMANANDA',
                department='Prod MC',
                section='Machining',
                role='Admin',
                is_approved=1
            )
            db.session.add(admin)
            db.session.commit()
            print('Admin user seeded.')


    @app.route('/')
    def index():
        resp = send_from_directory(app.static_folder, 'index.html')
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found'}), 404
        resp = send_from_directory(app.static_folder, 'index.html')
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    @app.route('/files/<path:filename>')
    def serve_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app

if __name__ == '__main__':
    app = create_app()
    try:
        from waitress import serve
        print('Starting Waitress server on http://0.0.0.0:5002...')
        serve(app, host='0.0.0.0', port=5002, threads=6)
    except Exception as e:
        print(f'Starting standard Flask on http://0.0.0.0:5002 (fallback: {e})...')
        app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
