import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PARENT_DIR = os.path.dirname(BASE_DIR)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(PARENT_DIR, "projects.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-prod'
    UPLOAD_FOLDER = os.path.join(PARENT_DIR, 'files')
    CORS_HEADERS = 'Content-Type'
