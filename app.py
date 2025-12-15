import streamlit as st
import sqlite3
from pathlib import Path
import pandas as pd
import datetime
import shutil
from io import BytesIO
import hashlib
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import fitz  # PyMuPDF
import re
from difflib import SequenceMatcher
import time

# --- Solusi: Atur st.set_page_config() hanya sekali di awal skrip ---
# Gunakan logika kondisional untuk menentukan layout berdasarkan status login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    st.set_page_config(
        page_title="Monitorix",
        page_icon="icon.png",
        layout="wide",
        initial_sidebar_state="expanded"
    )
else:
    st.set_page_config(
        page_title="Login",
        page_icon="icon.png",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

# --- Sisa Kode Aplikasi Anda (Tidak Berubah) ---

DB_PATH = Path("projects.db")
FILES_DIR = Path("files")
FILES_DIR.mkdir(exist_ok=True)

# Helper function untuk convert path ke relative path
def get_relative_path(file_path):
    """
    Convert absolute path menjadi relative path dari root aplikasi.
    Ini penting untuk kompatibilitas intranet - file harus diakses via relative path.
    """
    try:
        path = Path(file_path)
        app_root = Path(__file__).parent
        
        # Jika path sudah relative, return as is
        if not path.is_absolute():
            return str(path)
        
        # Try to make it relative to app root
        try:
            rel_path = path.relative_to(app_root)
            return str(rel_path)
        except ValueError:
            # Path is outside app root, return as is (not ideal but fallback)
            print(f"⚠️ Path berada di luar root aplikasi: {file_path}")
            return str(path)
    except Exception as e:
        print(f"❌ Error converting path: {e}")
        return str(file_path)

DEFAULT_DOC_COLUMNS = [
    'DRAWING', 'PIS', 'F DIM', 'FMEA', 'QCPC', 'PAR. PROCESS',
    'IK LV.3', 'ISIR', 'DATA SHEET', 'CAP. ANALAYST', 'LIST MEASURING INST.', 'MSA',
    'SPC / Pp PpK / Cp CpK', 'POKAYOKE', 'DWG JIG', 'REPORT TRIAL'
]

# Tentukan dokumen yang mendukung unggahan multiple files
MULTIPLE_FILE_DOCS = [
    'ISIR', 'DATA SHEET', 'CAP. ANALAYST', 'LIST MEASURING INST.', 'MSA',
    'SPC / Pp PpK / Cp CpK', 'POKAYOKE', 'DWG JIG', 'REPORT TRIAL'
]

BASE_COLUMNS = ['NO', 'ITEM', 'PART NO', 'PROJECT', 'CUSTOMER', 'STATUS', 'PIC']
PROJECT_STATUS = ['On Progress', 'Hold', 'Done', 'Canceled']
ROLES = ["Admin", "Manager", "SPV", "Staff"]

# --- Data Pengguna Default ---
DEFAULT_USERS = [
    ('0420', 'zzz', 'Wahyudi (Atmo)', 'Production  Machining', 'Mc Engineering', 'Manager', 1),
    ('0423', 'zzz', 'Tekat Rahayu', 'Production  Machining', 'Mc Engineering', 'SPV', 1),
    ('1839', 'zzz', 'Dhimas Rizal Saputra', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1044', 'zzz', 'Harsono', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1338', 'zzz', 'Eliek Wijaya', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1340', 'zzz', 'Ferry Pujowiyono', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1937', 'zzz', 'Fiki Yulian Cahyo', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1829', 'zzz', 'Galih Primananda', 'Production  Machining', 'Mc Engineering', 'Admin', 1),
    ('0899', 'zzz', 'Gatut Santosa', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1403', 'zzz', 'Kendy Kandra P.', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1941', 'zzz', 'Moch. Yongki Ardianto', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1837', 'zzz', 'Muhamad Akhsanul Kholikin', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1889', 'zzz', 'Muhamad Khoirul Huda', 'Production  Machining', 'Mc Engineering', 'Staff', 1),
    ('1804', 'zzz', 'Bagus Ajang Barokhah', 'Production  Machining', 'Mc Engineering', 'Spv', 1),
]

# --- CSS untuk Visualisasi Dashboard ---
st.markdown("""
<style>
    /* Global Styling */
    .main {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Stat Cards with Animation */
    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 160px;
        transition: all 0.3s ease;
        border: 1px solid rgba(0,0,0,0.05);
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
    }
    .stat-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }
    .stat-label {
        font-size: 15px;
        color: #666;
        font-weight: 600;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stat-delta {
        font-size: 13px;
        color: #888;
        font-weight: 500;
    }
    .stat-iconbox {
        width: 65px;
        height: 65px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: 20px;
        transition: all 0.3s ease;
    }
    .stat-card:hover .stat-iconbox {
        transform: scale(1.1) rotate(5deg);
    }
    
    /* Updated Colors with Gradients */
    .stat-iconbox.orange { background: linear-gradient(135deg, #fff7ed 0%, #fed7aa 100%); }
    .stat-iconbox.green { background: linear-gradient(135deg, #e6f9ed 0%, #bbf7d0 100%); }
    .stat-iconbox.blue { background: linear-gradient(135deg, #e6f0fa 0%, #bfdbfe 100%); }
    .stat-iconbox.purple { background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); }
    .stat-icon {
        width: 30px; height: 30px;
        stroke-width: 2.5;
    }
    .stat-icon.orange { color: #fb923c; }
    .stat-icon.green { color: #22c55e; }
    .stat-icon.blue { color: #2563eb; }
    .stat-icon.purple { color: #a21caf; }
    .stat-value.orange { color: #fb923c; font-weight: 700; }
    .stat-value.green { color: #22c55e; font-weight: 700; }
    .stat-value.blue { color: #2563eb; font-weight: 700; }
    .stat-value.purple { color: #a21caf; font-weight: 700; }
    
    /* Project Card Styling */
    .project-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        border-left: 4px solid #2563eb;
    }
    .project-card:hover {
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
        transform: translateX(5px);
    }
    .project-card.on-progress { border-left-color: #fb923c; }
    .project-card.done { border-left-color: #22c55e; }
    .project-card.hold { border-left-color: #94a3b8; }
    .project-card.canceled { border-left-color: #dc2626; }
    
    /* Badge Styling */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-badge.on-progress { background: #fff7ed; color: #fb923c; }
    .status-badge.done { background: #e6f9ed; color: #22c55e; }
    .status-badge.hold { background: #f1f5f9; color: #64748b; }
    .status-badge.canceled { background: #fee2e2; color: #dc2626; }
    
    /* Button Styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
        padding: 10px 24px;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
    }
    
    /* Form Styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 12px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb;
        color: white;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .streamlit-expanderHeader:hover {
        background-color: #e9ecef;
    }
    
    /* Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* Success/Error Messages */
    .stSuccess {
        background-color: #e6f9ed;
        border-left: 4px solid #22c55e;
        border-radius: 8px;
        padding: 16px;
    }
    .stError {
        background-color: #fee2e2;
        border-left: 4px solid #dc2626;
        border-radius: 8px;
        padding: 16px;
    }
    .stWarning {
        background-color: #fff7ed;
        border-left: 4px solid #fb923c;
        border-radius: 8px;
        padding: 16px;
    }
    .stInfo {
        background-color: #e6f0fa;
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        padding: 16px;
    }
    
    /* File Card Styling */
    .file-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #6366f1;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
    }
    .file-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        transform: translateX(3px);
    }
    .file-card.revision {
        border-left-color: #22c55e;
    }
    .file-icon {
        font-size: 24px;
        margin-right: 10px;
    }
    
    /* Download Button Styling */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    
    /* File Uploader Styling */
    .stFileUploader {
        background: #f8fafc;
        border: 2px dashed #cbd5e1;
        border-radius: 10px;
        padding: 20px;
        transition: all 0.3s ease;
    }
    .stFileUploader:hover {
        border-color: #6366f1;
        background: #f1f5f9;
    }
    
    /* Checkbox Styling */
    .stCheckbox {
        padding: 10px;
        background: #fef3c7;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
    }
    
    /* Progress Bar Styling */
    .stProgress > div > div {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        border-radius: 10px;
        height: 20px;
    }
    
    /* PDF Preview Grid Styling */
    .pdf-page-card {
        text-align: center;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .pdf-page-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    
    /* Expander Styling for Preview */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        font-weight: 600;
        padding: 15px;
    }
    
    /* Image container in grid */
    .stImage {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- Database helpers ---
def get_conn():
    return sqlite3.connect(DB_PATH)

def fetchall(query, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def parse_date_string(date_str):
    """Helper function to parse date string in DD-MM-YYYY or YYYY-MM-DD format"""
    if not date_str:
        return None
    try:
        # Try DD-MM-YYYY format first
        return datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
    except:
        try:
            # Fallback to YYYY-MM-DD format for backward compatibility
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None

def get_dynamic_doc_columns():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name FROM dynamic_docs")
    docs = [row[0] for row in c.fetchall()]
    conn.close()
    return docs

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    schema_users = (
        "CREATE TABLE IF NOT EXISTS users ("
        "id TEXT PRIMARY KEY,"
        "password TEXT,"
        "full_name TEXT,"
        "department TEXT,"
        "section TEXT,"
        "role TEXT,"
        "is_approved INTEGER DEFAULT 0"
        ")"
    )
    c.execute(schema_users)
    c.execute("CREATE TABLE IF NOT EXISTS dynamic_docs (name TEXT PRIMARY KEY)")

    current_docs = get_dynamic_doc_columns()
    
    # Kolom untuk single file
    single_file_docs = [doc for doc in DEFAULT_DOC_COLUMNS + current_docs if doc not in MULTIPLE_FILE_DOCS]
    doc_fields_single = [
        f"{col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_path TEXT, "
        f"{col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_date TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_delegated_to TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_start_date TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_end_date TEXT"
        for col in single_file_docs
    ]
    
    # Kolom untuk multiple files (menyimpan JSON string dari path)
    doc_fields_multiple = [
        f"{col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_paths TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_delegated_to TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_start_date TEXT"
        f", {col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_end_date TEXT"
        for col in MULTIPLE_FILE_DOCS
    ]
    
    all_doc_fields = doc_fields_single + doc_fields_multiple

    schema_projects = (
        "CREATE TABLE IF NOT EXISTS projects ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "item TEXT,"
        "part_no TEXT,"
        "project TEXT,"
        "customer TEXT,"
        "status TEXT,"
        "pic TEXT,"
        "project_start_date TEXT,"
        "project_end_date TEXT,"
        f"{', '.join(all_doc_fields)}, created_at TEXT, created_by TEXT"
        ")"
    )
    c.execute(schema_projects)

    schema_audit_logs = (
        "CREATE TABLE IF NOT EXISTS audit_logs ("
        "timestamp TEXT,"
        "user_id TEXT,"
        "action TEXT,"
        "details TEXT"
        ")"
    )
    c.execute(schema_audit_logs)
    
    schema_rev_hist = (
        "CREATE TABLE IF NOT EXISTS revision_history ("
        "project_id INTEGER,"
        "doc_column TEXT,"
        "revision_number INTEGER,"
        "file_path TEXT,"
        "timestamp TEXT,"
        "uploaded_by TEXT,"
        "upload_source TEXT,"
        "FOREIGN KEY(project_id) REFERENCES projects(id)"
        ")"
    )
    c.execute(schema_rev_hist)
    
    # Add upload_source column if it doesn't exist
    c.execute("PRAGMA table_info(revision_history)")
    rev_hist_cols = [col[1] for col in c.fetchall()]
    if 'upload_source' not in rev_hist_cols:
        c.execute("ALTER TABLE revision_history ADD COLUMN upload_source TEXT")
    
    schema_preferences = (
        "CREATE TABLE IF NOT EXISTS preferences ("
        "doc_name TEXT PRIMARY KEY,"
        "delegated_to TEXT"
        ")"
    )
    c.execute(schema_preferences)

    c.execute("PRAGMA table_info(projects)")
    cols_info = [info[1] for info in c.fetchall()]
    
    # Tambahkan kolom baru jika belum ada
    if 'project_start_date' not in cols_info:
        c.execute("ALTER TABLE projects ADD COLUMN project_start_date TEXT")
    if 'project_end_date' not in cols_info:
        c.execute("ALTER TABLE projects ADD COLUMN project_end_date TEXT")
    if 'approval_pending' not in cols_info:
        c.execute("ALTER TABLE projects ADD COLUMN approval_pending TEXT")
    if 'created_by' not in cols_info:
        c.execute("ALTER TABLE projects ADD COLUMN created_by TEXT")
    
    all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
    for col in all_docs:
        key = col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
        
        if col in MULTIPLE_FILE_DOCS:
            if f"{key}_paths" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_paths TEXT")
            if f"{key}_delegated_to" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_delegated_to TEXT")
            if f"{key}_start_date" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_start_date TEXT")
            if f"{key}_end_date" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_end_date TEXT")
        else:
            if f"{key}_path" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_path TEXT")
            if f"{key}_date" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_date TEXT")
            if f"{key}_delegated_to" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_delegated_to TEXT")
            if f"{key}_start_date" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_start_date TEXT")
            if f"{key}_end_date" not in cols_info:
                c.execute(f"ALTER TABLE projects ADD COLUMN {key}_end_date TEXT")

    # Tambahkan kolom list delegasi untuk semua dokumen jika belum ada
    for col in all_docs:
        key = col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
        if f"{key}_delegated_to_list" not in cols_info:
            c.execute(f"ALTER TABLE projects ADD COLUMN {key}_delegated_to_list TEXT")

    # Cek apakah tabel users kosong, jika ya tambahkan default users
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    
    if user_count == 0:
        # Hanya tambahkan default users jika tabel kosong
        add_default_users(c)

    conn.commit()
    conn.close()

def add_default_users(cursor):
    for user_data in DEFAULT_USERS:
        user_id, password, full_name, department, section, role, is_approved = user_data
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute(
                "INSERT INTO users (id, password, full_name, department, section, role, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, hashed_password, full_name, department, section, role, is_approved)
            )
        except sqlite3.IntegrityError:
            continue

def log_audit(user_id, action, details={}):
    conn = get_conn()
    c = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    # Filter out null or empty values for a cleaner log
    clean_details = {k: v for k, v in details.items() if v is not None and v != ''}
    if clean_details:
        details_json = json.dumps(clean_details)
        c.execute("INSERT INTO audit_logs (timestamp, user_id, action, details) VALUES (?, ?, ?, ?)",
                  (timestamp, user_id, action, details_json))
        conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

def get_user_by_id(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, user))
    return None

def get_all_users():
    conn = get_conn()
    df = pd.read_sql_query("SELECT id, full_name, department, section, role, is_approved FROM users", conn)
    conn.close()
    return df

def get_all_pids():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE is_approved = 1")
    pids = [row[0] for row in c.fetchall()]
    conn.close()
    return pids

def get_audit_logs():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# --- Preferensi Delegasi Otomatis ---
def get_all_preferences():
    conn = get_conn()
    df = pd.read_sql_query("SELECT doc_name, delegated_to FROM preferences", conn)
    conn.close()
    if df.empty:
        return []
    return df.to_dict(orient='records')

def upsert_preference(doc_name, delegated_to, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO preferences (doc_name, delegated_to) VALUES (?, ?) ON CONFLICT(doc_name) DO UPDATE SET delegated_to = excluded.delegated_to", (doc_name, delegated_to))
    conn.commit()
    conn.close()
    log_audit(user_id, "mengatur preferensi delegasi", {"doc_name": doc_name, "delegated_to": delegated_to})

def apply_preferences_to_all_projects(user_id):
    """
    Apply semua preferensi delegasi ke SEMUA proyek yang ada.
    Replace delegasi existing dengan preferensi yang telah diset.
    """
    conn = get_conn()
    c = conn.cursor()
    
    try:
        # Get all preferences
        prefs = get_all_preferences()
        if not prefs:
            return 0, "Tidak ada preferensi untuk diterapkan"
        
        # Get all projects
        c.execute("SELECT id FROM projects")
        projects = c.fetchall()
        
        if not projects:
            conn.close()
            return 0, "Tidak ada proyek yang perlu diupdate"
        
        updated_count = 0
        updated_details = []
        
        for pref in prefs:
            doc_name = pref['doc_name']
            delegated_to_raw = pref['delegated_to']
            
            # Parse delegated users
            try:
                delegated_list = json.loads(delegated_to_raw) if delegated_to_raw else []
                if isinstance(delegated_list, str):
                    delegated_list = [delegated_list]
            except (json.JSONDecodeError, TypeError):
                delegated_list = [delegated_to_raw] if delegated_to_raw else []
            
            if not delegated_list:
                continue
            
            # Prepare update values
            delegated_json = json.dumps(delegated_list)
            delegated_single = delegated_list[0]
            
            key = doc_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            
            # Update all projects
            for project in projects:
                project_id = project[0]
                
                # Update both delegated_to and delegated_to_list columns
                sql = f"UPDATE projects SET {key}_delegated_to = ?, {key}_delegated_to_list = ? WHERE id = ?"
                c.execute(sql, (delegated_single, delegated_json, project_id))
            
            updated_count += 1
            updated_details.append(f"{doc_name} → {', '.join(delegated_list)}")
        
        conn.commit()
        
        # Log audit
        log_audit(user_id, "apply preferensi ke semua proyek", {
            "total_projects": len(projects),
            "total_docs_updated": updated_count,
            "details": updated_details
        })
        
        return len(projects), f"Berhasil update {updated_count} dokumen untuk {len(projects)} proyek"
        
    except Exception as e:
        conn.rollback()
        return 0, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_preference(doc_name, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM preferences WHERE doc_name = ?", (doc_name,))
    conn.commit()
    conn.close()
    log_audit(user_id, "menghapus preferensi delegasi", {"doc_name": doc_name})
    
def get_revision_history(project_id, doc_column):
    conn = get_conn()
    c = conn.cursor()
    
    # Debug: Check what's in the table
    print(f"🔍 DEBUG - get_revision_history called with project_id={project_id}, doc_column={doc_column}")
    c.execute("SELECT * FROM revision_history WHERE project_id = ?", (project_id,))
    all_revs = c.fetchall()
    print(f"🔍 DEBUG - All revisions for project {project_id}: {all_revs}")
    
    # Join dengan tabel users untuk mendapatkan full_name
    c.execute("""
        SELECT rh.*, u.full_name 
        FROM revision_history rh 
        LEFT JOIN users u ON rh.uploaded_by = u.id 
        WHERE rh.project_id = ? AND rh.doc_column = ? 
        ORDER BY rh.revision_number DESC
    """, (project_id, doc_column))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    
    print(f"🔍 DEBUG - Found {len(rows)} rows for doc_column={doc_column}")
    
    if rows:
        result = []
        for row in rows:
            row_dict = dict(zip(cols, row))
            # Gunakan full_name jika ada, jika tidak gunakan uploaded_by (user_id)
            if row_dict.get('full_name'):
                row_dict['uploaded_by'] = row_dict['full_name']
            result.append(row_dict)
        return result
    return []

def register_user(user_id, password, full_name, department, section):
    conn = get_conn()
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        # Set is_approved = 0 secara eksplisit untuk user baru
        c.execute("INSERT INTO users (id, password, full_name, department, section, role, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (user_id, hashed_password, full_name, department, section, 'Staff', 0))
        conn.commit()
        conn.close()
        log_audit(user_id, "registrasi akun baru", {"full_name": full_name, "department": department})
        # Invalidate cache untuk refresh user list
        if 'cached_pids' in st.session_state:
            del st.session_state['cached_pids']
        if 'cached_pids_manage' in st.session_state:
            del st.session_state['cached_pids_manage']
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
    except Exception as e:
        conn.close()
        print(f"Error registering user: {e}")
        return False

def approve_user(user_id, admin_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    log_audit(admin_id, "menyetujui pengguna", {"approved_user_id": user_id})
    # Invalidate cache untuk refresh user list
    if 'cached_pids' in st.session_state:
        del st.session_state['cached_pids']
    if 'cached_pids_manage' in st.session_state:
        del st.session_state['cached_pids_manage']

def update_user_role(user_id, new_role, admin_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    log_audit(admin_id, "mengubah role pengguna", {"user_id": user_id, "new_role": new_role})
    
def reset_user_password(user_id, new_password, admin_id):
    conn = get_conn()
    c = conn.cursor()
    hashed_password = hash_password(new_password)
    c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
    conn.commit()
    conn.close()
    log_audit(admin_id, "mereset password pengguna", {"user_id": user_id})

# --- Login & Register Pages ---
def show_login_page():
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1>🔐 Login ke Sistem</h1>
        <p style='color: #666;'>Project Monitoring IATF</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        user_id_input = st.text_input("👤 User ID", placeholder="Masukkan User ID Anda")
        password_input = st.text_input("🔒 Password", type="password", placeholder="Masukkan Password")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if user_id_input and password_input:
                    user = get_user_by_id(user_id_input)
                    
                    if user:
                        # Cek apakah user sudah di-approve
                        if user['is_approved'] == 0:
                            st.error("❌ Akun Anda belum disetujui oleh Admin. Silakan hubungi Admin untuk approval.")
                        elif verify_password(password_input, user['password']):
                            st.session_state['logged_in'] = True
                            st.session_state['user_id'] = user_id_input
                            st.session_state['user_role'] = user['role']
                            st.session_state['user_full_name'] = user['full_name']
                            log_audit(user_id_input, "login", {})
                            st.success(f"✅ Selamat datang, {user['full_name']}!")
                            st.rerun()
                        else:
                            st.error("❌ Password salah!")
                    else:
                        st.error("❌ User ID tidak ditemukan!")
                else:
                    st.warning("⚠️ Mohon isi User ID dan Password!")
        
        with col_btn2:
            if st.button("📝 Register", use_container_width=True):
                st.session_state['page'] = 'register'
                st.rerun()
        
        st.markdown("---")
        st.info("💡 **Info:** Jika belum memiliki akun, silakan Register terlebih dahulu dan tunggu approval dari Admin.")

def show_register_page():
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1>📝 Registrasi Akun Baru</h1>
        <p style='color: #666;'>Daftar untuk menggunakan sistem</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        with st.form(key='register_form'):
            reg_user_id = st.text_input("👤 User ID *", placeholder="Contoh: 1234", help="Masukkan NIK atau User ID unik")
            reg_full_name = st.text_input("👨 Nama Lengkap *", placeholder="Nama Lengkap Anda")
            reg_department = st.text_input("🏢 Department *", placeholder="Contoh: Production Machining")
            reg_section = st.text_input("📋 Section *", placeholder="Contoh: Mc Engineering")
            reg_password = st.text_input("🔒 Password *", type="password", placeholder="Min. 3 karakter")
            reg_password_confirm = st.text_input("🔒 Konfirmasi Password *", type="password", placeholder="Masukkan ulang password")
            
            st.markdown("---")
            col_submit1, col_submit2 = st.columns(2)
            
            with col_submit1:
                submit_register = st.form_submit_button("✅ Daftar", use_container_width=True, type="primary")
            with col_submit2:
                back_to_login = st.form_submit_button("◀️ Kembali", use_container_width=True)
        
        if back_to_login:
            st.session_state['page'] = 'login'
            st.rerun()
        
        if submit_register:
            if not all([reg_user_id, reg_full_name, reg_department, reg_section, reg_password, reg_password_confirm]):
                st.error("❌ Semua field wajib diisi!")
            elif len(reg_password) < 3:
                st.error("❌ Password minimal 3 karakter!")
            elif reg_password != reg_password_confirm:
                st.error("❌ Password tidak cocok!")
            else:
                # Cek apakah User ID sudah digunakan
                existing_user = get_user_by_id(reg_user_id)
                if existing_user:
                    st.error(f"❌ User ID **{reg_user_id}** sudah terdaftar!")
                else:
                    # Register user baru dengan is_approved = 0 (pending)
                    result = register_user(reg_user_id, reg_password, reg_full_name, reg_department, reg_section)
                    if result:
                        st.success(f"✅ Registrasi berhasil! Akun **{reg_full_name}** telah dibuat.")
                        st.info("⏳ **Mohon menunggu approval dari Admin** untuk dapat login.")
                        st.balloons()
                        import time
                        time.sleep(2)
                        st.session_state['page'] = 'login'
                        st.rerun()
                    else:
                        st.error("❌ Gagal melakukan registrasi. Silakan coba lagi.")

def show_main_page():
    # Sidebar Navigation
    st.sidebar.markdown(f"""
    <div style='text-align: center; padding: 10px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
                border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: white; margin: 0;'>👤 {st.session_state.get('user_full_name', 'User')}</h3>
        <p style='color: #e0e0e0; margin: 0; font-size: 14px;'>Role: {st.session_state.get('user_role', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu navigation
    menu_options = ["🏠 Dashboard", "📤 Upload Dokumen", "✅ Approval List"]
    
    role = st.session_state.get('user_role')
    if role in ['Admin', 'Manager', 'SPV']:
        menu_options.append("🔧 Manajemen Proyek")
    if role in ['Admin', 'Manager']:
        menu_options.append("📊 Audit Log")
    if role in ['Admin']:
        menu_options.extend(["👥 Kelola User", "⚙️ Preferensi Delegasi"])
    
    menu_options.append("📥 Export Data")
    menu_options.append("🚪 Logout")
    
    choice = st.sidebar.radio("📋 Menu", menu_options, label_visibility="collapsed")
    
    # Route ke halaman yang dipilih
    if choice == "🏠 Dashboard":
        show_dashboard()
    elif choice == "📤 Upload Dokumen":
        upload_doc_form()
    elif choice == "✅ Approval List":
        show_approval_list()
    elif choice == "🔧 Manajemen Proyek":
        show_management_tab()
    elif choice == "📊 Audit Log":
        show_audit_log_page()
    elif choice == "👥 Kelola User":
        manage_users_page()
    elif choice == "⚙️ Preferensi Delegasi":
        show_preferences_page()
    elif choice == "📥 Export Data":
        export_data_page()
    elif choice == "🚪 Logout":
        log_audit(st.session_state['user_id'], "logout", {})
        st.session_state['logged_in'] = False
        st.session_state['page'] = 'login'
        st.rerun()

# --- Dashboard Page ---
def show_dashboard():
    st.header("🏠 Dashboard - Project Monitoring IATF")
    
    df_view = load_df()
    
    if df_view.empty:
        st.info("📭 Belum ada proyek dalam sistem. Silakan tambah proyek terlebih dahulu.")
        return
    
    # Statistik Cards
    total_projects = len(df_view)
    on_progress = len(df_view[df_view['STATUS'] == 'On Progress'])
    done = len(df_view[df_view['STATUS'] == 'Done'])
    hold = len(df_view[df_view['STATUS'] == 'Hold'])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Proyek", total_projects, help="Jumlah keseluruhan proyek")
    with col2:
        st.metric("On Progress", on_progress, help="Proyek yang sedang berjalan")
    with col3:
        st.metric("Done", done, help="Proyek yang sudah selesai")
    with col4:
        st.metric("Hold", hold, help="Proyek yang ditunda")
    with col5:
        # Hitung proyek yang hampir selesai (progress >= 80% tapi belum Done)
        near_completion = 0
        all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        total_docs = len(all_docs)
        
        for _, row in df_view.iterrows():
            if row['STATUS'] not in ['Done', 'Canceled']:
                completed = sum(1 for col in all_docs if row.get(col, {}).get('path' if col not in MULTIPLE_FILE_DOCS else 'paths'))
                progress = (completed / total_docs * 100) if total_docs > 0 else 0
                if progress >= 80:
                    near_completion += 1
        
        st.metric("Hampir Selesai", near_completion, help="Proyek dengan progress ≥80%")
    
    # Info box untuk auto-complete
    if near_completion > 0:
        st.info(f"ℹ️ Ada **{near_completion} proyek** yang hampir selesai (progress ≥80%). Status akan otomatis berubah menjadi 'Done' ketika semua dokumen lengkap.")
    
    st.markdown("---")
    
    # Tabel Proyek
    st.markdown("### 📋 Daftar Proyek")
    display_cols = ['NO', 'ITEM', 'PART NO', 'PROJECT', 'CUSTOMER', 'STATUS', 'PIC']
    st.dataframe(df_view[display_cols], use_container_width=True, hide_index=True)

# --- User Management Page ---
def manage_users_page():
    st.header("👥 Kelola User")
    
    user_tabs = st.tabs(["➕ Tambah User", "📋 Daftar User", "✅ Approve User", "⚙️ Edit User"])
    
    # Tab 1: Tambah User
    with user_tabs[0]:
        st.markdown("### ➕ Tambah Pengguna Baru")
        st.info("💡 Admin dapat menambahkan user baru langsung dengan opsi auto-approve")
        
        with st.form(key='add_user_form'):
            col1, col2 = st.columns(2)
            with col1:
                new_user_id = st.text_input("User ID *", placeholder="Contoh: 1234")
                new_full_name = st.text_input("Nama Lengkap *", placeholder="Nama lengkap pengguna")
                new_department = st.text_input("Department *", placeholder="Contoh: Production Machining")
            with col2:
                new_section = st.text_input("Section *", placeholder="Contoh: Mc Engineering")
                new_role = st.selectbox("Role *", ROLES, index=3)  # Default: Staff
                new_password = st.text_input("Password *", type="password", placeholder="Min. 3 karakter")
            
            auto_approve = st.checkbox("✅ Auto-approve user ini (langsung bisa login)", value=True)
            
            submitted = st.form_submit_button("✅ Tambah User", use_container_width=True, type="primary")
            
            if submitted:
                if not all([new_user_id, new_full_name, new_department, new_section, new_password]):
                    st.error("❌ Semua field wajib diisi!")
                elif len(new_password) < 3:
                    st.error("❌ Password minimal 3 karakter!")
                else:
                    existing_user = get_user_by_id(new_user_id)
                    if existing_user:
                        st.error(f"❌ User dengan ID **{new_user_id}** sudah terdaftar!")
                    else:
                        try:
                            # Register user baru
                            result = register_user(new_user_id, new_password, new_full_name, new_department, new_section)
                            
                            if result:
                                # Update role jika bukan Staff (default) - SEBELUM approve
                                if new_role != "Staff":
                                    update_user_role(new_user_id, new_role, st.session_state['user_id'])
                                
                                # Auto approve jika dipilih
                                if auto_approve:
                                    approve_user(new_user_id, st.session_state['user_id'])
                                    st.success(f"✅ User **{new_full_name}** ({new_user_id}) berhasil ditambahkan dan disetujui!")
                                    st.info(f"📋 Role: **{new_role}** | Status: **Approved** | User sudah bisa login")
                                else:
                                    st.success(f"✅ User **{new_full_name}** ({new_user_id}) berhasil ditambahkan! Menunggu approval.")
                                    st.info(f"📋 Role: **{new_role}** | Status: **Pending Approval** | Perlu approve untuk login")
                                
                                st.balloons()
                                
                                # Verifikasi data tersimpan
                                verify_user = get_user_by_id(new_user_id)
                                if verify_user:
                                    st.success(f"✅ Verifikasi: Data tersimpan! is_approved = {verify_user['is_approved']}, role = {verify_user['role']}")
                                else:
                                    st.error("⚠️ Warning: Data mungkin tidak tersimpan dengan benar")
                                
                                # Auto rerun untuk refresh data
                                st.rerun()
                            else:
                                st.error("❌ Gagal menambahkan user. ID mungkin sudah digunakan.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            import traceback
                            st.error(f"Debug: {traceback.format_exc()}")
    
    # Tab 2: Daftar User
    with user_tabs[1]:
        # Load data users fresh
        users_df = get_all_users()
        
        st.markdown("### 📋 Daftar Semua Pengguna")
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            # Statistik User
            total_users = len(users_df)
            approved_users = len(users_df[users_df['is_approved'] == 1])
            pending_users_count = len(users_df[users_df['is_approved'] == 0])
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Total Users", total_users, help="Total pengguna terdaftar")
            with col_stat2:
                st.metric("Approved", approved_users, help="User yang sudah disetujui")
            with col_stat3:
                st.metric("Pending", pending_users_count, delta="Need Action" if pending_users_count > 0 else None, help="User menunggu approval")
            
            st.markdown("---")
            st.dataframe(users_df, use_container_width=True, hide_index=True)
    
    # Tab 3: Approve User
    with user_tabs[2]:
        # Load data users fresh
        users_df = get_all_users()
        
        st.markdown("### ✅ Setujui Pengguna Baru")
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            pending_users = users_df[users_df['is_approved'] == 0]
            if not pending_users.empty:
                st.warning(f"⚠️ Ada {len(pending_users)} pengguna yang menunggu persetujuan!")
                
                col_approve1, col_approve2 = st.columns([2, 1])
                with col_approve1:
                    user_to_approve = st.selectbox(
                        "Pilih pengguna untuk disetujui",
                        pending_users['id'].tolist(),
                        format_func=lambda x: f"{x} - {pending_users[pending_users['id']==x]['full_name'].iloc[0]}"
                    )
                with col_approve2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✅ Approve User", use_container_width=True):
                        approve_user(user_to_approve, st.session_state['user_id'])
                        st.success(f"✅ Pengguna **{user_to_approve}** berhasil disetujui!")
                        st.rerun()
            else:
                st.success("✅ Semua pengguna sudah disetujui!")
    
    # Tab 4: Edit User
    with user_tabs[3]:
        # Load data users fresh
        users_df = get_all_users()
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            st.markdown("### ⚙️ Ubah Role & Password Pengguna")
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                user_to_edit = st.selectbox(
                    "Pilih pengguna untuk di-edit",
                    users_df['id'].tolist(),
                    format_func=lambda x: f"{x} - {users_df[users_df['id']==x]['full_name'].iloc[0]}"
                )
            
            if user_to_edit:
                with col_edit2:
                    current_role = users_df[users_df['id'] == user_to_edit]['role'].iloc[0]
                    st.info(f"**Role saat ini:** {current_role}")
                
                st.markdown("---")
                st.markdown("#### 🔄 Ubah Role")
                col_role1, col_role2 = st.columns([2, 1])
                with col_role1:
                    new_role = st.selectbox("Pilih Role Baru", ROLES, index=ROLES.index(current_role))
                with col_role2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Simpan Role", use_container_width=True):
                        update_user_role(user_to_edit, new_role, st.session_state['user_id'])
                        st.success(f"✅ Role pengguna **{user_to_edit}** berhasil diubah menjadi **{new_role}**!")
                        st.rerun()
                
                st.markdown("---")
                st.markdown("#### 🔐 Reset Password")
                new_password = st.text_input(f"Password Baru untuk {user_to_edit}", type="password", key=f"new_pass_{user_to_edit}", placeholder="Min. 3 karakter")
                if st.button("🔄 Reset Password", type="primary"):
                    if new_password:
                        if len(new_password) < 3:
                            st.error("❌ Password minimal 3 karakter!")
                        else:
                            reset_user_password(user_to_edit, new_password, st.session_state['user_id'])
                            st.success(f"✅ Password untuk **{user_to_edit}** berhasil di-reset!")
                    else:
                        st.warning("⚠️ Masukkan password baru terlebih dahulu!")

# --- Preferences Page ---
def show_preferences_page():
    st.header("⚙️ Preferensi Delegasi")
    
    col_info, col_refresh = st.columns([4, 1])
    with col_info:
        st.info("💡 Atur delegasi default untuk dokumen tertentu (bisa lebih dari 1 user)")
    with col_refresh:
        if st.button("🔄 Refresh Data", help="Muat ulang daftar user terbaru"):
            st.session_state['pref_refresh'] = True
            st.rerun()
    
    # Cache preferences dan users di session_state untuk menghindari query berulang
    # Auto-refresh jika cache tidak ada (user baru approved/registered)
    if ('cached_prefs' not in st.session_state or 
        'cached_pids' not in st.session_state or 
        st.session_state.get('pref_refresh', False)):
        st.session_state['cached_prefs'] = get_all_preferences()
        st.session_state['cached_pids'] = get_all_pids()
        st.session_state['pref_refresh'] = False
    
    prefs = st.session_state['cached_prefs']
    pids = st.session_state['cached_pids']
    
    if prefs:
        st.markdown("##### Preferensi Saat Ini")
        # Parse JSON untuk menampilkan multiple users
        prefs_display = []
        for p in prefs:
            try:
                users_list = json.loads(p['delegated_to']) if p['delegated_to'] else []
                if isinstance(users_list, str):
                    users_list = [users_list]
                users_str = ", ".join(users_list) if users_list else "-"
            except (json.JSONDecodeError, TypeError):
                users_str = p['delegated_to'] if p['delegated_to'] else "-"
            prefs_display.append({
                'doc_name': p['doc_name'],
                'delegated_to': users_str
            })
        st.dataframe(pd.DataFrame(prefs_display), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada preferensi delegasi yang disetel.")
    
    st.markdown("---")
    st.markdown("##### Tambah/Perbarui Preferensi")
    all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
    pref_doc = st.selectbox("Dokumen", all_docs, key="pref_doc_select")
    
    # Get existing preference untuk dokumen ini
    existing_pref = next((p for p in prefs if p['doc_name'] == pref_doc), None)
    existing_users = []
    if existing_pref:
        try:
            existing_users = json.loads(existing_pref['delegated_to']) if existing_pref['delegated_to'] else []
            if isinstance(existing_users, str):
                existing_users = [existing_users]
        except (json.JSONDecodeError, TypeError):
            existing_users = [existing_pref['delegated_to']] if existing_pref['delegated_to'] else []
    
    pref_users = st.multiselect(
        "Delegasikan ke (bisa pilih lebih dari 1)",
        pids,
        default=[u for u in existing_users if u in pids],
        key="pref_user_select"
    )
    
    if st.button("💾 Simpan Preferensi"):
        if pref_users:
            # Simpan sebagai JSON string
            users_json = json.dumps(pref_users)
            upsert_preference(pref_doc, users_json, st.session_state['user_id'])
            st.success(f"✅ Preferensi tersimpan: **{pref_doc}** → {', '.join(pref_users)}")
            # Refresh cache agar data terbaru muncul
            st.session_state['pref_refresh'] = True
            st.rerun()
        else:
            st.error("❌ Pilih minimal 1 user untuk delegasi!")
    
    st.markdown("---")
    st.markdown("##### 🔄 Terapkan Preferensi ke Semua Proyek")
    st.warning("⚠️ **Perhatian!** Fitur ini akan **mengganti delegasi** di SEMUA proyek dengan preferensi yang telah Anda set di atas.")
    
    col_apply1, col_apply2 = st.columns([3, 1])
    with col_apply1:
        st.info(f"📊 Jumlah preferensi yang akan diterapkan: **{len(prefs)}** dokumen")
    with col_apply2:
        if st.button("🚀 Apply ke Semua Proyek", type="primary", use_container_width=True):
            with st.spinner("Sedang menerapkan preferensi ke semua proyek..."):
                project_count, message = apply_preferences_to_all_projects(st.session_state['user_id'])
                
                if project_count > 0:
                    st.success(f"✅ {message}")
                    st.balloons()
                    
                    # Show details
                    with st.expander("📋 Detail Update"):
                        for p in prefs:
                            try:
                                users_list = json.loads(p['delegated_to']) if p['delegated_to'] else []
                                if isinstance(users_list, str):
                                    users_list = [users_list]
                                users_str = ", ".join(users_list) if users_list else "-"
                            except (json.JSONDecodeError, TypeError):
                                users_str = p['delegated_to'] if p['delegated_to'] else "-"
                            st.write(f"✓ **{p['doc_name']}** → {users_str}")
                    
                    st.info("💡 Silakan cek menu **Dashboard** atau **Manajemen Proyek** untuk melihat perubahan.")
                else:
                    st.error(f"❌ {message}")
    
    st.markdown("---")
    st.markdown("##### Hapus Preferensi")
    if prefs:
        doc_to_remove = st.selectbox("Pilih dokumen untuk dihapus preferensinya", [p['doc_name'] for p in prefs], key="pref_doc_remove")
        if st.button("🗑️ Hapus Preferensi"):
            delete_preference(doc_to_remove, st.session_state['user_id'])
            st.success("✅ Preferensi dihapus.")
            # Refresh cache agar data terbaru muncul
            st.session_state['pref_refresh'] = True
            st.rerun()
    else:
        st.info("Tidak ada preferensi untuk dihapus.")

# --- Export Data Page ---
def export_data_page():
    st.header("📥 Export Data")
    st.info("💡 Download data proyek dalam format Excel")
    
    df_view = load_df()
    
    if df_view.empty:
        st.warning("Tidak ada data untuk diekspor.")
    else:
        st.success(f"✅ Ditemukan **{len(df_view)}** proyek untuk diekspor")
        
        # Export semua data
        if st.button("📥 Download Excel", type="primary"):
            rows = []
            for _, r in df_view.iterrows():
                base = {c: r[c] for c in ['NO', 'ITEM', 'PART NO', 'PROJECT', 'CUSTOMER', 'STATUS', 'PIC', 'PROJECT START DATE', 'PROJECT END DATE']}
                all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
                for col in all_doc_cols:
                    cell = r.get(col, {})
                    if col in MULTIPLE_FILE_DOCS:
                        base[col + ' - PATHS'] = json.dumps(cell.get('paths')) if cell.get('paths') else ""
                    else:
                        base[col + ' - PATH'] = cell.get('path', "")
                        base[col + ' - DATE'] = cell.get('date', "")
                    
                    base[col + ' - DELEGATED_TO'] = cell.get('delegated_to', "")
                    base[col + ' - START_DATE'] = cell.get('start_date', "")
                    base[col + ' - END_DATE'] = cell.get('end_date', "")
                rows.append(base)
            out_df = pd.DataFrame(rows)
            buf = BytesIO()
            out_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button('📥 Download .xlsx', data=buf, file_name='project_monitor_export.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            st.success("File siap diunduh!")

def add_dynamic_doc_column(col_name, user_id):
    conn = get_conn()
    c = conn.cursor()
    key = col_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    
    is_multiple = col_name in MULTIPLE_FILE_DOCS
    
    try:
        c.execute("INSERT INTO dynamic_docs (name) VALUES (?)", (col_name,))
        if is_multiple:
            c.execute(f"ALTER TABLE projects ADD COLUMN {key}_paths TEXT")
        else:
            c.execute(f"ALTER TABLE projects ADD COLUMN {key}_path TEXT")
            c.execute(f"ALTER TABLE projects ADD COLUMN {key}_date TEXT")
        
        c.execute(f"ALTER TABLE projects ADD COLUMN {key}_delegated_to TEXT")
        c.execute(f"ALTER TABLE projects ADD COLUMN {key}_start_date TEXT")
        c.execute(f"ALTER TABLE projects ADD COLUMN {key}_end_date TEXT")
        
        conn.commit()
        log_audit(user_id, "menambah kolom dokumen", {"doc_name": col_name, "is_multiple": is_multiple})
        return True
    except sqlite3.OperationalError as e:
        st.error(f"Kolom sudah ada atau ada kesalahan: {e}")
        return False
    except sqlite3.IntegrityError:
        st.error("Kolom sudah ada.")
        return False
    finally:
        conn.close()

def delete_doc_column(col_name, user_id):
    conn = get_conn()
    c = conn.cursor()
    key = col_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    
    try:
        # Hapus dari tabel dynamic_docs jika ada
        c.execute("DELETE FROM dynamic_docs WHERE name = ?", (col_name,))
        
        st.warning("Menghapus kolom memerlukan pembuatan ulang tabel. Ini akan memakan waktu sejenap.")
        
        all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        new_docs = [doc for doc in all_docs if doc != col_name]

        # Buat daftar kolom baru
        new_cols_to_copy = []
        base_cols_to_copy = ['id', 'item', 'part_no', 'project', 'customer', 'status', 'pic', 'project_start_date', 'project_end_date', 'created_at']
        new_cols_to_copy.extend(base_cols_to_copy)
        
        doc_fields_single = []
        doc_fields_multiple = []

        for doc in new_docs:
            doc_key = doc.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            if doc in MULTIPLE_FILE_DOCS:
                doc_fields_multiple.append(f"{doc_key}_paths TEXT")
                doc_fields_multiple.append(f"{doc_key}_delegated_to TEXT")
                doc_fields_multiple.append(f"{doc_key}_start_date TEXT")
                doc_fields_multiple.append(f"{doc_key}_end_date TEXT")
                new_cols_to_copy.append(f"{doc_key}_paths")
                new_cols_to_copy.append(f"{doc_key}_delegated_to")
                new_cols_to_copy.append(f"{doc_key}_start_date")
                new_cols_to_copy.append(f"{doc_key}_end_date")
            else:
                doc_fields_single.append(f"{doc_key}_path TEXT")
                doc_fields_single.append(f"{doc_key}_date TEXT")
                doc_fields_single.append(f"{doc_key}_delegated_to TEXT")
                doc_fields_single.append(f"{doc_key}_start_date TEXT")
                doc_fields_single.append(f"{doc_key}_end_date TEXT")
                new_cols_to_copy.append(f"{doc_key}_path")
                new_cols_to_copy.append(f"{doc_key}_date")
                new_cols_to_copy.append(f"{doc_key}_delegated_to")
                new_cols_to_copy.append(f"{doc_key}_start_date")
                new_cols_to_copy.append(f"{doc_key}_end_date")
        
        all_new_doc_fields = doc_fields_single + doc_fields_multiple

        schema_temp_projects = (
            "CREATE TABLE temp_projects ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "item TEXT,"
            "part_no TEXT,"
            "project TEXT,"
            "customer TEXT,"
            "status TEXT,"
            "pic TEXT,"
            "project_start_date TEXT,"
            "project_end_date TEXT,"
            f"{', '.join(all_new_doc_fields)}, created_at TEXT"
            ")"
        )
        c.execute(schema_temp_projects)

        c.execute(f"""
            INSERT INTO temp_projects({', '.join(new_cols_to_copy)})
            SELECT {', '.join(new_cols_to_copy)}
            FROM projects
        """)

        c.execute("DROP TABLE projects")
        c.execute("ALTER TABLE temp_projects RENAME TO projects")
        
        conn.commit()
        log_audit(user_id, "menghapus kolom dokumen", {"doc_name": col_name})
        return True
    except Exception as e:
        st.error(f"Gagal menghapus kolom: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# --- Fungsi Manajemen Proyek ---
def load_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    
    # Load preferensi delegasi
    preferences_df = pd.read_sql_query("SELECT doc_name, delegated_to FROM preferences", conn)
    conn.close()
    
    # Buat dictionary untuk mapping preferensi (support multiple users)
    preferences_map = {}
    if not preferences_df.empty:
        for _, pref in preferences_df.iterrows():
            try:
                # Parse JSON untuk multiple users
                users_list = json.loads(pref['delegated_to']) if pref['delegated_to'] else []
                if isinstance(users_list, str):
                    users_list = [users_list]
                users_str = ", ".join(users_list) if users_list else None
                preferences_map[pref['doc_name']] = users_str
            except (json.JSONDecodeError, TypeError):
                # Fallback ke string biasa jika bukan JSON
                preferences_map[pref['doc_name']] = pref['delegated_to']
    
    current_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
    if df.empty:
        return pd.DataFrame(columns=BASE_COLUMNS + current_docs)

    display_rows = []
    for _, r in df.iterrows():
        row = {
            'NO': r['id'],
            'ITEM': r['item'],
            'PART NO': r['part_no'],
            'PROJECT': r['project'],
            'CUSTOMER': r.get('customer', 'N/A'),
            'STATUS': r.get('status', 'N/A'),
            'PIC': r.get('pic', 'N/A'),
            'PROJECT START DATE': r.get('project_start_date', 'N/A'),
            'PROJECT END DATE': r.get('project_end_date', 'N/A')
        }
        for col in current_docs:
            key = col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            
            if col in MULTIPLE_FILE_DOCS:
                raw_paths = r.get(f"{key}_paths")
                if raw_paths is None or raw_paths == "":
                    paths = []
                else:
                    try:
                        paths = json.loads(raw_paths)
                    except json.JSONDecodeError:
                        paths = []
                doc_status = "✅ Lengkap" if paths else "⏳ Belum Selesai"
                delegated_json = r.get(f"{key}_delegated_to_list")
                try:
                    delegated_list = json.loads(delegated_json) if delegated_json else []
                except json.JSONDecodeError:
                    delegated_list = []
                
                # Fallback ke single delegated_to jika list kosong
                if not delegated_list:
                    single_delegated = r.get(f"{key}_delegated_to", None)
                    if single_delegated and single_delegated != "None":
                        delegated_list = [single_delegated]
                
                # Fallback ke preferensi default jika masih kosong
                if not delegated_list:
                    pref_value = preferences_map.get(col, None)
                    if pref_value and pref_value != "None":
                        # Pref value bisa berupa string comma-separated
                        delegated_list = [u.strip() for u in pref_value.split(',')] if ',' in pref_value else [pref_value]
                
                delegated_display = ", ".join(delegated_list) if delegated_list else "N/A"
                
                row[col] = {
                    'paths': paths,
                    'status': doc_status,
                    'delegated_to': delegated_display,
                    'delegated_to_list': delegated_list,
                    'start_date': r.get(f"{key}_start_date", r.get('project_start_date')), 
                    'end_date': r.get(f"{key}_end_date", r.get('project_end_date'))
                }
            else:
                path = r.get(f"{key}_path", None)
                doc_status = "✅ Lengkap" if path else "⏳ Belum Selesai"
                delegated_json = r.get(f"{key}_delegated_to_list")
                try:
                    delegated_list = json.loads(delegated_json) if delegated_json else []
                except json.JSONDecodeError:
                    delegated_list = []
                
                # Fallback ke single delegated_to jika list kosong
                if not delegated_list:
                    single_delegated = r.get(f"{key}_delegated_to", None)
                    if single_delegated and single_delegated != "None":
                        delegated_list = [single_delegated]
                
                # Fallback ke preferensi default jika masih kosong
                if not delegated_list:
                    pref_value = preferences_map.get(col, None)
                    if pref_value and pref_value != "None":
                        # Pref value bisa berupa string comma-separated
                        delegated_list = [u.strip() for u in pref_value.split(',')] if ',' in pref_value else [pref_value]
                
                delegated_display = ", ".join(delegated_list) if delegated_list else "N/A"
                
                row[col] = {
                    'path': path, 
                    'date': r.get(f"{key}_date", None), 
                    'status': doc_status,
                    'delegated_to': delegated_display,
                    'delegated_to_list': delegated_list,
                    'start_date': r.get(f"{key}_start_date", r.get('project_start_date')), 
                    'end_date': r.get(f"{key}_end_date", r.get('project_end_date'))
                }
        display_rows.append(row)
    
    display_df = pd.DataFrame(display_rows)
    return display_df

def insert_row(item, part_no, project, customer, status, pic, project_start_date, project_end_date, user_id):
    conn = get_conn()
    c = conn.cursor()
    fields = ['item', 'part_no', 'project', 'customer', 'status', 'pic', 'project_start_date', 'project_end_date', 'created_at']
    placeholders = ['?'] * len(fields)
    values = [item, part_no, project, customer, status, pic, project_start_date, project_end_date, datetime.datetime.now().isoformat()]
    
    sql = f"INSERT INTO projects ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
    c.execute(sql, values)
    new_project_id = c.lastrowid

    # Terapkan preferensi delegasi otomatis
    try:
        prefs = get_all_preferences()
        for pref in prefs:
            doc_name = pref['doc_name']
            raw = pref['delegated_to']
            delegates = []
            try:
                delegates = json.loads(raw) if isinstance(raw, str) else (raw or [])
            except json.JSONDecodeError:
                delegates = [raw] if raw else []
            key = doc_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            delegated_json = json.dumps(delegates) if delegates else None
            delegated_single = delegates[0] if delegates else None
            c.execute(f"UPDATE projects SET {key}_delegated_to = ?, {key}_delegated_to_list = ? WHERE id = ?", (delegated_single, delegated_json, new_project_id))
        # commit setelah seluruh update preferensi
        conn.commit()
    except Exception as e:
        # Jangan gagalkan penambahan proyek bila preferensi gagal
        conn.commit()
        st.warning(f"Preferensi delegasi gagal diterapkan: {e}")

    conn.close()
    log_audit(user_id, "menambah proyek", {
        "project_id": int(new_project_id),
        "project_name": project,
        "item": item,
        "part_no": part_no,
        "customer": customer,
        "pic": pic
    })

def delete_row(row_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (row_id,))
    result = c.fetchone()
    project_name, item, part_no = result if result else ("N/A", "N/A", "N/A")
    c.execute("DELETE FROM projects WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    log_audit(user_id, "menghapus proyek", {
        "project_id": int(row_id),
        "project_name": project_name,
        "item": item,
        "part_no": part_no
    })

def update_row(row_id, item, part_no, project, customer, status, pic, project_start_date, project_end_date, user_id):
    conn = get_conn()
    c = conn.cursor()
    sql = "UPDATE projects SET item = ?, part_no = ?, project = ?, customer = ?, status = ?, pic = ?, project_start_date = ?, project_end_date = ? WHERE id = ?"
    c.execute(sql, (item, part_no, project, customer, status, pic, project_start_date, project_end_date, row_id))
    conn.commit()
    conn.close()
    log_audit(user_id, "mengedit proyek", {
        "project_id": int(row_id),
        "project_name": project,
        "item": item,
        "part_no": part_no,
        "status": status
    })

def update_row_delegation(row_id, doc_col, delegated_to, start_date, end_date, user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (row_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None
    
    key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    
    # Normalisasi ke list
    if isinstance(delegated_to, list):
        delegated_list = [d for d in delegated_to if d]
    elif delegated_to:
        delegated_list = [delegated_to]
    else:
        delegated_list = []
    delegated_json = json.dumps(delegated_list) if delegated_list else None
    delegated_single = delegated_list[0] if delegated_list else None

    sql = f"UPDATE projects SET {key}_delegated_to = ?, {key}_delegated_to_list = ?, {key}_start_date = ?, {key}_end_date = ? WHERE id = ?"
    c.execute(sql, (delegated_single, delegated_json, start_date, end_date, row_id))
    conn.commit()
    conn.close()
    
    # Hanya log jika ada perubahan delegasi
    if delegated_list:
        log_audit(user_id, "mendelegasikan dokumen", {"project_id": int(row_id), "project_name": project_name, "item": item, "part_no": part_no, "doc_column": doc_col, "delegated_to": delegated_list, "start_date": start_date, "end_date": end_date})

def check_and_update_project_status(project_id, user_id):
    """
    Mengecek kelengkapan semua dokumen dalam proyek.
    Jika semua dokumen sudah terisi/lengkap, otomatis update status menjadi 'Done'.
    """
    conn = get_conn()
    c = conn.cursor()
    
    try:
        # Get current project status
        c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        if not result:
            conn.close()
            return
        
        current_status = result[0]
        
        # Skip jika sudah Done atau Canceled
        if current_status in ['Done', 'Canceled']:
            conn.close()
            return
        
        # Get all document columns
        all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        
        # Check completeness
        all_complete = True
        
        for doc_col in all_docs:
            key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            
            if doc_col in MULTIPLE_FILE_DOCS:
                # Check multiple file documents
                c.execute(f"SELECT {key}_paths FROM projects WHERE id = ?", (project_id,))
                res = c.fetchone()
                if res and res[0]:
                    try:
                        paths = json.loads(res[0])
                        if not paths:  # Empty list
                            all_complete = False
                            break
                    except (json.JSONDecodeError, TypeError):
                        all_complete = False
                        break
                else:
                    all_complete = False
                    break
            else:
                # Check single file documents
                c.execute(f"SELECT {key}_path FROM projects WHERE id = ?", (project_id,))
                res = c.fetchone()
                if not res or not res[0]:
                    all_complete = False
                    break
        
        # Update status jika semua dokumen lengkap
        if all_complete and current_status != 'Done':
            c.execute("UPDATE projects SET status = ? WHERE id = ?", ('Done', project_id))
            conn.commit()
            log_audit(user_id, "auto-update status proyek", {
                "project_id": project_id, 
                "old_status": current_status, 
                "new_status": "Done",
                "reason": "Semua dokumen lengkap"
            })
            
            # Tampilkan notifikasi di UI
            st.success(f"🎉 **Proyek #{project_id} otomatis diubah menjadi Done!** Semua dokumen sudah lengkap.")
    
    except Exception as e:
        st.warning(f"Gagal auto-update status: {e}")
    finally:
        conn.close()

def approve_uploaded_file(row_id, doc_col, temp_path, user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (row_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None
    
    key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    
    # Check if this is a multiple file document
    if doc_col in MULTIPLE_FILE_DOCS:
        # For multiple file documents, add to existing paths JSON
        c.execute(f"SELECT {key}_paths FROM projects WHERE id = ?", (row_id,))
        current_paths_json = c.fetchone()[0]
        
        current_paths = []
        if current_paths_json:
            try:
                current_paths = json.loads(current_paths_json)
            except json.JSONDecodeError:
                current_paths = []
        
        # Add new file to paths - gunakan relative path
        current_paths.append(get_relative_path(temp_path))
        
        # Update projects table with new paths
        sql = f"UPDATE projects SET {key}_paths = ? WHERE id = ?"
        c.execute(sql, (json.dumps(current_paths), row_id))
        
        # Delete pending entry from revision_history
        c.execute("DELETE FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1 AND file_path = ?", 
                  (row_id, doc_col, temp_path))
        
    else:
        # For single file documents, use revision system
        c.execute("SELECT MAX(revision_number) FROM revision_history WHERE project_id = ? AND doc_column = ?", (row_id, doc_col))
        max_rev = c.fetchone()[0]
        new_rev = (max_rev or 0) + 1
        
        # Hapus entry pending
        c.execute("DELETE FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1", (row_id, doc_col))

        # Update revision_history with the new revision number - gunakan relative path
        relative_path = get_relative_path(temp_path)
        c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                  (row_id, doc_col, new_rev, relative_path, datetime.datetime.now().isoformat(), st.session_state['user_id']))

        # Update projects table with the new file path and date
        sql = f"UPDATE projects SET {key}_path = ?, {key}_date = ? WHERE id = ?"
        c.execute(sql, (relative_path, datetime.date.today().strftime('%d-%m-%Y'), row_id))

    conn.commit()
    conn.close()
    
    log_audit(user_id, "menyetujui dokumen", {
        "project_id": int(row_id), 
        "project_name": project_name, 
        "item": item, 
        "part_no": part_no, 
        "doc_column": doc_col, 
        "approved_file": temp_path,
        "is_multiple_file_doc": doc_col in MULTIPLE_FILE_DOCS
    })
    
    # Auto-update status jika semua dokumen lengkap
    check_and_update_project_status(row_id, user_id)
    
def reject_uploaded_file(project_id, doc_column, file_path, user_id):
    conn = get_conn()
    c = conn.cursor()

    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (project_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None

    # Hapus entri dari revision_history
    c.execute("DELETE FROM revision_history WHERE project_id = ? AND doc_column = ? AND file_path = ?",
              (project_id, doc_column, file_path))
    
    # Hapus file fisik dari direktori
    try:
        os.remove(file_path)
    except OSError as e:
        st.warning(f"Gagal menghapus file fisik: {e}")
    
    conn.commit()
    conn.close()
    log_audit(user_id, "menolak dokumen", {"project_id": int(project_id), "project_name": project_name, "item": item, "part_no": part_no, "doc_column": doc_column, "rejected_file": file_path})


def cancel_pending_file(project_id, doc_column, user_id):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT file_path, uploaded_by FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1",
            (project_id, doc_column)
        )
        rows = c.fetchall()
        if not rows:
            conn.close()
            st.warning("Tidak ada pengajuan pending untuk dibatalkan.")
            return False

        role = st.session_state.get('user_role')
        allowed = any((uploaded_by == user_id) or (role in ['Admin', 'Manager']) for (file_path, uploaded_by) in rows)
        if not allowed:
            conn.close()
            st.warning("Anda tidak memiliki izin untuk membatalkan pengajuan ini.")
            return False

        for file_path, uploaded_by in rows:
            if (uploaded_by == user_id) or (role in ['Admin', 'Manager']):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                c.execute(
                    "DELETE FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1 AND file_path = ?",
                    (project_id, doc_column, file_path)
                )

        conn.commit()
        conn.close()
        log_audit(user_id, "membatalkan pengajuan dokumen", {"project_id": project_id, "doc_column": doc_column})
        return True
    except Exception as e:
        conn.close()
        st.error(f"Gagal membatalkan pengajuan: {e}")
        return False


def upload_file_and_save_as_pending(project_id, doc_column, uploaded_file, user_id):
    conn = get_conn()
    c = conn.cursor()

    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (project_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None

    dest_dir = FILES_DIR / f"project_{project_id}" / "temp_uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = uploaded_file.name
    dest_path = dest_dir / f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)
    
    # Simpan sebagai relative path untuk kompatibilitas intranet
    relative_path = get_relative_path(dest_path)
    
    c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
              (project_id, doc_column, -1, relative_path, datetime.datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()
    
    log_audit(user_id, "mengunggah file pending", {"project_id": int(project_id), "project_name": project_name, "item": item, "part_no": part_no, "doc_column": doc_column, "file_path": str(dest_path), "file_name": safe_name})
    
    return str(dest_path)

def upload_multiple_files_for_doc(project_id, doc_column, uploaded_files, user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (project_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None
    
    key = doc_column.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    
    c.execute(f"SELECT {key}_paths FROM projects WHERE id = ?", (project_id,))
    current_paths_json = c.fetchone()[0]

    current_paths = []
    if current_paths_json:
        try:
            current_paths = json.loads(current_paths_json)
        except json.JSONDecodeError:
            current_paths = []

    
    new_paths = []
    
    for uploaded_file in uploaded_files:
        dest_dir = FILES_DIR / f"project_{project_id}" / doc_column.replace(' ', '_')
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Buat nama file unik dengan timestamp dan nama asli
        unique_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
        dest_path = dest_dir / unique_name
        
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(uploaded_file, f)
        
        # Gunakan relative path untuk kompatibilitas intranet
        new_paths.append(get_relative_path(dest_path))
        
        log_audit(user_id, "mengunggah file", {
            "project_id": int(project_id),
            "project_name": project_name,
            "item": item,
            "part_no": part_no,
            "doc_column": doc_column,
            "file_name": uploaded_file.name,
            "file_path": str(dest_path)
        })
    
    # Gabungkan path baru dengan path lama
    updated_paths = current_paths + new_paths
    
    # Simpan kembali ke database dalam format JSON
    sql = f"UPDATE projects SET {key}_paths = ? WHERE id = ?"
    c.execute(sql, (json.dumps(updated_paths), project_id))
    
    conn.commit()
    conn.close()
    
    # Auto-update status jika semua dokumen lengkap
    check_and_update_project_status(project_id, user_id)
    
    return True


def delete_file_from_multiple_doc(project_id, doc_column, file_path, user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Fetch project details for logging
    c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (project_id,))
    proj_row = c.fetchone()
    project_name = proj_row[0] if proj_row else None
    item = proj_row[1] if proj_row else None
    part_no = proj_row[2] if proj_row else None
    
    key = doc_column.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
    try:
        c.execute(f"SELECT {key}_paths, {key}_delegated_to FROM projects WHERE id = ?", (project_id,))
        res = c.fetchone()
        if not res:
            conn.close()
            st.error("Proyek tidak ditemukan.")
            return False
        paths_json, delegated_to = res
        current_paths = []
        if paths_json:
            try:
                current_paths = json.loads(paths_json)
            except json.JSONDecodeError:
                current_paths = []
        role = st.session_state.get('user_role')
        current_user = get_user_by_id(user_id)
        current_name = current_user['full_name'] if current_user else None
        allowed = role in ['Admin', 'Manager'] or (delegated_to and current_name == delegated_to)
        if not allowed:
            conn.close()
            st.warning("Anda tidak memiliki izin untuk menghapus file ini.")
            return False
        if file_path not in current_paths:
            conn.close()
            st.warning("File tidak ditemukan pada daftar dokumen.")
            return False
        updated_paths = [p for p in current_paths if p != file_path]
        try:
            os.remove(file_path)
        except OSError:
            pass
        c.execute(f"UPDATE projects SET {key}_paths = ? WHERE id = ?", (json.dumps(updated_paths), project_id))
        conn.commit()
        conn.close()
        log_audit(user_id, "menghapus file dokumen multiple", {"project_id": int(project_id), "project_name": project_name, "item": item, "part_no": part_no, "doc_column": doc_column, "deleted_file": file_path})
        return True
    except Exception as e:
        conn.close()
        st.error(f"Gagal menghapus file: {e}")
        return False


def get_row_details(row_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM projects WHERE id = ?', (row_id,))
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    conn.close()
    if row:
        return dict(zip(cols, row))
    return None

def get_file_content(file_path):
    """
    Membaca konten file dan mengembalikan bytes.
    Menangani berbagai kasus error seperti file tidak ada, permission error, dll.
    Mendukung relative dan absolute path untuk kompatibilitas intranet.
    """
    try:
        # Convert to Path object
        path = Path(file_path)
        
        # Jika path tidak absolute, anggap relative dari root aplikasi
        if not path.is_absolute():
            # Path relative dari direktori aplikasi
            path = Path(__file__).parent / path
        
        # Cek apakah file exists
        if not path.exists():
            print(f"❌ File tidak ditemukan: {file_path}")
            print(f"   Full path yang dicoba: {path.absolute()}")
            return None
        
        # Cek apakah path adalah file (bukan directory)
        if not path.is_file():
            print(f"❌ Path bukan file: {file_path}")
            return None
        
        # Baca file dalam binary mode
        with open(path, "rb") as file:
            content = file.read()
            
            # Validasi bahwa file memiliki konten
            if not content:
                print(f"⚠️ File kosong: {file_path}")
                return b''  # Return empty bytes instead of None
            
            print(f"✅ File berhasil dibaca: {file_path} ({len(content)} bytes)")
            return content
            
    except PermissionError:
        print(f"❌ Permission denied: {file_path}")
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Error membaca file {file_path}: {str(e)}")
        return None

def render_pdf_as_images(pdf_path, max_pages=5, zoom=2.0):
    """
    Render PDF pages as images using PyMuPDF
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to render (default 5)
        zoom: Zoom factor for rendering quality (default 2.0)
    Returns:
        Tuple of (List of PIL Images, total page count)
    """
    doc = None
    try:
        # Konversi path ke string jika Path object
        pdf_path_str = str(pdf_path)
        
        # Validasi file exists
        if not os.path.exists(pdf_path_str):
            raise FileNotFoundError(f"PDF file not found: {pdf_path_str}")
        
        # Buka dokumen PDF
        doc = fitz.open(pdf_path_str)
        total_pages = doc.page_count  # Lebih reliable daripada len()
        images = []
        
        if total_pages == 0:
            return [], 0
        
        # Limit to max_pages
        num_pages = min(total_pages, max_pages)
        
        for page_num in range(num_pages):
            try:
                page = doc.load_page(page_num)  # load_page lebih eksplisit
                
                # Create transformation matrix for zoom
                mat = fitz.Matrix(zoom, zoom)
                
                # Render page to pixmap with better settings
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
                
                # Free pixmap memory
                del pix
                
            except Exception as page_error:
                # Skip halaman yang error, lanjut ke halaman berikutnya
                continue
        
        return images, total_pages
        
    except FileNotFoundError as e:
        raise e
    except Exception as e:
        # Log error untuk debugging
        import traceback
        print(f"Error in render_pdf_as_images: {str(e)}")
        print(traceback.format_exc())
        return [], 0
    finally:
        # Pastikan dokumen ditutup
        if doc is not None:
            try:
                doc.close()
            except:
                pass

# --- UI Halaman Login & Register ---
def show_login_page():
    # Centered layout dengan kolom
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo dan Header
        try:
            st.image("logo.png", width=300)
        except:
            pass
        
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <h1 style='color: #2563eb; font-size: 2.5em; margin-bottom: 5px;'>🔐 Monitorix</h1>
            <p style='color: #64748b; font-size: 1.2em;'>Project Monitoring IATF System</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        with st.form(key='login_form'):
            st.markdown("#### 👤 Masuk ke Akun Anda")
            
            user_id = st.text_input(
                "User ID",
                placeholder="Masukkan User ID (contoh: 1234)",
                key="login_id",
                help="User ID terdiri dari 4 digit angka"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan password Anda",
                key="login_pass",
                help="Password bersifat case-sensitive"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit_button:
                if not user_id or not password:
                    st.error("⚠️ Mohon lengkapi User ID dan Password.")
                else:
                    user = get_user_by_id(user_id)
                    if user and verify_password(password, user['password']):
                        if user['is_approved'] == 1:
                            st.session_state['logged_in'] = True
                            st.session_state['user_id'] = user['id']
                            st.session_state['user_role'] = user['role']
                            st.session_state['user_name'] = user['full_name']
                            st.session_state['user_dept'] = user['department']
                            st.session_state['user_section'] = user['section']
                            log_audit(user_id, "login berhasil")
                            st.success(f"✅ Selamat datang, {user['full_name']}! 🎉")
                            st.rerun()
                        else:
                            st.warning("⏳ Akun Anda sedang menunggu persetujuan Administrator. Harap bersabar.")
                    else:
                        log_audit(user_id, "login gagal")
                        st.error("❌ User ID atau password salah. Silakan coba lagi.")

        st.markdown("---")
        
        # Register section dengan styling yang lebih menarik
        st.markdown("""
        <div style='text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>
            <p style='color: #64748b; margin-bottom: 10px;'>Belum punya akun?</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📝 Daftar Akun Baru", use_container_width=True):
            st.session_state['page'] = 'register'
            st.rerun()

def show_register_page():
    # Centered layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo dan Header
        try:
            st.image("logo.png", width=300)
        except:
            pass
        
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <h1 style='color: #2563eb; font-size: 2.5em; margin-bottom: 5px;'>📝 Daftar Akun</h1>
            <p style='color: #64748b; font-size: 1.1em;'>Buat akun baru untuk mengakses Monitorix</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("ℹ️ **Catatan:** Setelah mendaftar, akun Anda akan direview dan disetujui oleh Administrator.")
        
        st.markdown("---")
        
        with st.form(key='register_form'):
            st.markdown("#### 🆔 Informasi Login")
            
            user_id = st.text_input(
                "User ID (4 karakter) *",
                max_chars=4,
                placeholder="Contoh: 1234",
                help="User ID harus terdiri dari 4 digit angka atau karakter alphanumeric"
            )
            
            col_pass1, col_pass2 = st.columns(2)
            with col_pass1:
                password = st.text_input(
                    "Password *",
                    type="password",
                    placeholder="Min. 6 karakter",
                    help="Gunakan kombinasi huruf, angka, dan simbol untuk keamanan"
                )
            with col_pass2:
                confirm_password = st.text_input(
                    "Konfirmasi Password *",
                    type="password",
                    placeholder="Ulangi password",
                    help="Pastikan password sama dengan yang diatas"
                )
            
            st.markdown("---")
            st.markdown("#### 👤 Informasi Pribadi")
            
            full_name = st.text_input(
                "Nama Lengkap *",
                placeholder="Contoh: Galih Primananda",
                help="Nama lengkap sesuai identitas resmi"
            )
            
            col_dept, col_sec = st.columns(2)
            with col_dept:
                department = st.text_input(
                    "Departemen *",
                    placeholder="Contoh: Production Machining",
                    help="Departemen tempat Anda bekerja"
                )
            with col_sec:
                section = st.text_input(
                    "Seksi *",
                    placeholder="Contoh: Mc Engineering",
                    help="Seksi atau divisi di departemen"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("✅ Daftar Sekarang", use_container_width=True)
            
            if submit_button:
                # Validasi input
                if not user_id or not full_name or not password or not confirm_password or not department or not section:
                    st.error("⚠️ **Semua field wajib diisi.** Mohon lengkapi formulir.")
                elif len(user_id) != 4:
                    st.error("⚠️ **User ID harus terdiri dari 4 karakter.**")
                elif len(password) < 6:
                    st.error("⚠️ **Password minimal 6 karakter.**")
                elif password != confirm_password:
                    st.error("⚠️ **Konfirmasi password tidak cocok.** Periksa kembali password Anda.")
                else:
                    if register_user(user_id, password, full_name, department, section):
                        st.success(f"✅ **Registrasi berhasil, {full_name}!** Tunggu persetujuan Admin untuk login.")
                        st.balloons()
                        st.session_state['page'] = 'login'
                        st.rerun()
                    else:
                        st.error("❌ **User ID sudah terdaftar.** Gunakan User ID lain atau hubungi Admin.")

        st.markdown("---")
        
        # Login section
        st.markdown("""
        <div style='text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>
            <p style='color: #64748b; margin-bottom: 10px;'>Sudah punya akun?</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔐 Login Sekarang", use_container_width=True):
            st.session_state['page'] = 'login'
            st.rerun()

def show_main_page():
    # --- Identitas Pengguna di Sidebar ---
    with st.sidebar:
        try:
            st.image("logo.png", width=500)
        except:
            st.markdown("### 🔧 Monitorix")
        
        # Profile Card dengan styling yang lebih menarik
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;'>
            <h3 style='margin: 0; color: white;'>👤 Profil Pengguna</h3>
        </div>
        """, unsafe_allow_html=True)
        
        user_role = st.session_state.get('user_role', 'N/A')
        role_emoji = {'Admin': '👑', 'Manager': '⭐', 'SPV': '🔰', 'Staff': '👨‍💼'}
        
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 15px;'>
            <p style='margin: 5px 0;'><b>📛 Nama:</b> {st.session_state.get('user_name', 'User')}</p>
            <p style='margin: 5px 0;'><b>{role_emoji.get(user_role, '👤')} Role:</b> {user_role}</p>
            <p style='margin: 5px 0;'><b>🏢 Departemen:</b> {st.session_state.get('user_dept', 'N/A')}</p>
            <p style='margin: 5px 0;'><b>📂 Seksi:</b> {st.session_state.get('user_section', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Actions dengan icon yang jelas
        st.markdown("### ⚡ Quick Actions")
        
        if st.session_state['user_role'] in ['Admin', 'Manager', 'SPV']:
            if st.button("📋 Cek Dokumen Pending", use_container_width=True, help="Lihat dokumen yang menunggu approval"):
                st.session_state['current_view'] = 'approval_list'
                st.rerun()

        if st.button("📊 Dashboard Proyek", use_container_width=True, help="Kembali ke halaman dashboard"):
            st.session_state['current_view'] = 'dashboard'
            st.rerun()
        
        st.markdown("---")
        
        # Logout button dengan style khusus
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            log_audit(st.session_state.get('user_id'), "logout")
            st.session_state.clear()
            st.rerun()

    # Welcome Message dengan gradient
    st.markdown(f"""
    <div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 15px; color: white; margin-bottom: 20px;'>
        <h1 style='margin: 0; color: white;'>👋 Selamat Datang, {st.session_state.get('user_name', 'User')}!</h1>
        <p style='margin: 10px 0 0 0; opacity: 0.9;'>Role: {st.session_state.get('user_role', 'N/A')} | 
        Departemen: {st.session_state.get('user_dept', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    if 'current_view' not in st.session_state:
        st.session_state['current_view'] = 'dashboard'
    
    if st.session_state['current_view'] == 'approval_list' and st.session_state['user_role'] in ['Admin', 'Manager', 'SPV']:
        show_approval_list()
    elif st.session_state['user_role'] in ['Admin', 'Manager']:
        admin_tabs = st.tabs([
            "📊 Dashboard Proyek", 
            "🔧 Manajemen Proyek", 
            "👥 Manajemen User", 
            "📄 Manajemen Dokumen", 
            "📝 Audit Log"
        ])
        
        with admin_tabs[0]:
            show_dashboard_tab()
        with admin_tabs[1]:
            show_management_tab()
        with admin_tabs[2]:
            manage_users_page()
        with admin_tabs[3]:
            manage_docs_page()
        with admin_tabs[4]:
            show_audit_log_page()
    elif st.session_state['user_role'] == 'SPV':
        spv_tabs = st.tabs([
            "📊 Dashboard Proyek", 
            "🔧 Manajemen Proyek", 
            "📝 Audit Log"
        ])
        with spv_tabs[0]:
            show_dashboard_tab()
        with spv_tabs[1]:
            show_management_tab()
        with spv_tabs[2]:
            show_audit_log_page()
    else: # Staff
        staff_tabs = st.tabs([
            "📊 Dashboard Proyek", 
            "📤 Upload Dokumen"
        ])
        with staff_tabs[0]:
            show_dashboard_tab()
        with staff_tabs[1]:
            upload_doc_form()

# --- Fungsi untuk halaman approval ---
def show_approval_list():
    st.title("📋 Daftar Dokumen Pending Approval")
    st.caption("Review dan setujui dokumen yang diunggah oleh tim")
    
    user_name = get_user_by_id(st.session_state['user_id'])['full_name']
    
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT rh.project_id, rh.doc_column, rh.file_path, rh.uploaded_by, rh.timestamp,
                 p.project, p.item, p.part_no, p.customer, rh.upload_source 
                 FROM revision_history rh 
                 JOIN projects p ON rh.project_id = p.id 
                 WHERE rh.revision_number = -1
                 ORDER BY p.project, rh.timestamp DESC""")
    pending_files = c.fetchall()
    conn.close()
    
    if not pending_files:
        st.success("✅ Semua dokumen sudah diproses!")
        st.info("Tidak ada dokumen yang menunggu persetujuan saat ini.")
        return

    # Filter dan Search Bar
    col_search, col_filter, col_view = st.columns([2, 2, 1])
    
    with col_search:
        search_query = st.text_input("🔍 Cari Dokumen", placeholder="Cari berdasarkan nama proyek, item, atau customer...", key="search_approval")
    
    with col_filter:
        doc_types = list(set([doc[1] for doc in pending_files]))
        doc_types.insert(0, "Semua Dokumen")
        filter_doc = st.selectbox("📁 Filter Tipe Dokumen", doc_types, key="filter_doc_type")
    
    with col_view:
        view_mode = st.radio("👁️ View", ["Compact", "Detail"], horizontal=True, key="view_mode_approval")
    
    # Counter statistik dengan styling
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; text-align: center; color: white;'>
            <h2 style='margin: 0; color: white;'>{len(pending_files)}</h2>
            <p style='margin: 5px 0 0 0; opacity: 0.9;'>Total Pending</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.info("💡 Hanya dokumen yang didelegasikan kepada Anda atau dokumen yang diunggah oleh Staff yang bisa Anda setujui.")
    
    # Bulk Actions: Approve All / Reject All
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #6366f1;'>
        <h3 style='margin: 0 0 10px 0; color: #333;'>⚡ Aksi Massal</h3>
        <p style='margin: 0; font-size: 13px; color: #666;'>Setujui atau tolak semua dokumen sesuai filter yang diterapkan</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_bulk1, col_bulk2, col_bulk3 = st.columns([1, 1, 3])
    
    with col_bulk1:
        if st.button("✅ Setujui Semua", type="primary", use_container_width=True, key="approve_all_btn"):
            st.session_state['confirm_approve_all'] = True
    
    with col_bulk2:
        if st.button("❌ Tolak Semua", use_container_width=True, key="reject_all_btn"):
            st.session_state['confirm_reject_all'] = True
    
    # Confirmation dialogs
    if st.session_state.get('confirm_approve_all', False):
        st.warning("⚠️ Anda akan menyetujui SEMUA dokumen pending yang sesuai filter. Lanjutkan?")
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ Ya, Setujui Semua", type="primary", use_container_width=True, key="confirm_approve_all_yes"):
                # Will be processed after filtering
                st.session_state['execute_approve_all'] = True
                st.session_state['confirm_approve_all'] = False
                st.rerun()
        with col_confirm2:
            if st.button("🚫 Batal", use_container_width=True, key="confirm_approve_all_no"):
                st.session_state['confirm_approve_all'] = False
                st.rerun()
    
    if st.session_state.get('confirm_reject_all', False):
        st.error("⚠️ Anda akan menolak SEMUA dokumen pending yang sesuai filter. Lanjutkan?")
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("❌ Ya, Tolak Semua", type="primary", use_container_width=True, key="confirm_reject_all_yes"):
                # Will be processed after filtering
                st.session_state['execute_reject_all'] = True
                st.session_state['confirm_reject_all'] = False
                st.rerun()
        with col_confirm2:
            if st.button("🚫 Batal", use_container_width=True, key="confirm_reject_all_no"):
                st.session_state['confirm_reject_all'] = False
                st.rerun()
    
    st.divider()
    
    # Group documents by project untuk tampilan yang lebih terorganisir
    docs_by_project = {}
    filtered_docs = []
    
    for pending_data in pending_files:
        project_id, doc_col, file_path, uploaded_by, timestamp, project_name, item, part_no, customer, upload_source = pending_data
        
        # Apply filters
        if search_query:
            if search_query.lower() not in project_name.lower() and \
               search_query.lower() not in item.lower() and \
               search_query.lower() not in customer.lower():
                continue
        
        if filter_doc != "Semua Dokumen" and doc_col != filter_doc:
            continue
        
        row_data = get_row_details(project_id)
        delegated_to_name = row_data.get(f"{doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')}_delegated_to")
        
        is_approver = False
        if st.session_state['user_role'] in ['Admin', 'Manager']:
            is_approver = True
        else:
            key_chk = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
            delegated_list_json = row_data.get(f"{key_chk}_delegated_to_list")
            try:
                delegated_list = json.loads(delegated_list_json) if delegated_list_json else ([] if not delegated_to_name else [delegated_to_name])
            except json.JSONDecodeError:
                delegated_list = ([] if not delegated_to_name else [delegated_to_name])
            if st.session_state['user_role'] == 'SPV' and user_name in delegated_list:
                is_approver = True
        
        if is_approver:
            if project_name not in docs_by_project:
                docs_by_project[project_name] = []
            docs_by_project[project_name].append(pending_data)
            filtered_docs.append(pending_data)
    
    if not filtered_docs:
        st.warning("🔍 Tidak ada dokumen yang sesuai dengan filter.")
        return
    
    # Execute bulk actions
    if st.session_state.get('execute_approve_all', False):
        success_count = 0
        fail_count = 0
        
        with st.spinner(f"🔄 Memproses {len(filtered_docs)} dokumen..."):
            for pending_data in filtered_docs:
                project_id, doc_col, file_path, uploaded_by, timestamp, project_name, item, part_no, customer, upload_source = pending_data
                try:
                    approve_uploaded_file(project_id, doc_col, file_path, st.session_state['user_id'])
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    st.error(f"❌ Gagal menyetujui {doc_col} - {project_name}: {str(e)}")
        
        st.session_state['execute_approve_all'] = False
        
        if success_count > 0:
            st.success(f"✅ Berhasil menyetujui {success_count} dokumen!")
        if fail_count > 0:
            st.error(f"❌ Gagal menyetujui {fail_count} dokumen")
        
        st.balloons()
        time.sleep(1)
        st.rerun()
    
    if st.session_state.get('execute_reject_all', False):
        success_count = 0
        fail_count = 0
        
        with st.spinner(f"🔄 Memproses {len(filtered_docs)} dokumen..."):
            for pending_data in filtered_docs:
                project_id, doc_col, file_path, uploaded_by, timestamp, project_name, item, part_no, customer, upload_source = pending_data
                try:
                    reject_uploaded_file(project_id, doc_col, file_path, st.session_state['user_id'])
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    st.error(f"❌ Gagal menolak {doc_col} - {project_name}: {str(e)}")
        
        st.session_state['execute_reject_all'] = False
        
        if success_count > 0:
            st.warning(f"⚠️ Berhasil menolak {success_count} dokumen")
        if fail_count > 0:
            st.error(f"❌ Gagal menolak {fail_count} dokumen")
        
        time.sleep(1)
        st.rerun()
    
    st.success(f"✅ Menampilkan {len(filtered_docs)} dokumen")
    
    # Display documents individually with full details (not grouped by project)
    for idx, pending_data in enumerate(filtered_docs):
        project_id, doc_col, file_path, uploaded_by, timestamp, project_name, item, part_no, customer, upload_source = pending_data
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        uploader_info = get_user_by_id(uploaded_by)
        uploader_name = uploader_info['full_name'] if uploader_info else uploaded_by
        
        # Determine upload source label
        source_badge = ""
        if upload_source == "auto_upload":
            source_badge = "<span style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px;'>🤖 AUTO</span>"
        else:
            source_badge = "<span style='background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px;'>📤 MANUAL</span>"
        
        # Create detailed title with Item, Part Number, Project
        title_text = f"📄 {item or 'N/A'} | 📊 {part_no or 'N/A'} | 💼 {project_name or 'N/A'}"
        
        with st.expander(f"**{title_text}** - {doc_col}", expanded=False):
            # Compact or Detail view
            if view_mode == "Compact":
                # Compact Card View
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                            border-left: 4px solid #667eea;
                            border-radius: 10px;
                            padding: 15px;
                            margin: 10px 0;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div style='flex: 1;'>
                            <h4 style='margin: 0; color: #667eea;'>📄 {doc_col} {source_badge}</h4>
                            <p style='margin: 8px 0 4px 0; font-size: 14px; color: #333;'>
                                <strong>📦 Item:</strong> {item or 'N/A'} | 
                                <strong>🔢 Part No:</strong> {part_no or 'N/A'}
                            </p>
                            <p style='margin: 4px 0; font-size: 13px; color: #666;'>
                                <strong>💼 Project:</strong> {project_name or 'N/A'} | 
                                <strong>🏭 Customer:</strong> {customer or 'N/A'}
                            </p>
                            <p style='margin: 8px 0 0 0; font-size: 12px; color: #888;'>
                                📎 {file_name} | 👤 {uploader_name} | ⏰ {timestamp[:16]}
                            </p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Detail View
                source_badge_text = "🤖 AUTO UPLOAD" if upload_source == "auto_upload" else "📤 MANUAL UPLOAD"
                source_color = "#10b981" if upload_source == "auto_upload" else "#6366f1"
                
                st.markdown(f"### 📄 {doc_col}")
                st.markdown(f"<span style='background: {source_color}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 12px; font-weight: 600;'>{source_badge_text}</span>", unsafe_allow_html=True)
                st.caption(f"File: {file_name} | ⏳ Status: PENDING")
                
                st.markdown("---")
                
                # Project Information - More detailed
                st.markdown("#### 📁 Informasi Proyek")
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;'>
                        <p style='margin: 0; font-size: 13px; color: #666;'><strong>📦 Item:</strong></p>
                        <p style='margin: 4px 0 0 0; font-size: 16px; color: #333; font-weight: 600;'>{item or 'N/A'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 12px; border-radius: 8px;'>
                        <p style='margin: 0; font-size: 13px; color: #666;'><strong>💼 Project:</strong></p>
                        <p style='margin: 4px 0 0 0; font-size: 16px; color: #333; font-weight: 600;'>{project_name or 'N/A'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_info2:
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;'>
                        <p style='margin: 0; font-size: 13px; color: #666;'><strong>🔢 Part Number:</strong></p>
                        <p style='margin: 4px 0 0 0; font-size: 16px; color: #333; font-weight: 600;'>{part_no or 'N/A'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 12px; border-radius: 8px;'>
                        <p style='margin: 0; font-size: 13px; color: #666;'><strong>🏭 Customer:</strong></p>
                        <p style='margin: 4px 0 0 0; font-size: 16px; color: #333; font-weight: 600;'>{customer or 'N/A'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Upload Information
                st.markdown("#### 📄 Informasi Upload")
                col_upload1, col_upload2 = st.columns(2)
                
                with col_upload1:
                    st.write("**👤 Uploader:**", uploader_name)
                    st.write("**📎 Nama File:**", file_name)
                
                with col_upload2:
                    st.write("**⏰ Waktu Upload:**", timestamp[:16])
                    st.write("**📂 Dokumen:**", doc_col)
                
            # Action buttons - Always shown
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            
            with col1:
                # Get file content dengan error handling
                file_content = get_file_content(file_path)
                
                if file_content is not None:
                    st.download_button(
                        label="⬇️ Download",
                        data=file_content,
                        file_name=file_name,
                        key=f"dl_approve_{idx}_{project_id}_{doc_col}",
                        use_container_width=True,
                        help=f"Download file: {file_name}"
                    )
                else:
                    st.button(
                        "⬇️ Download", 
                        disabled=True, 
                        key=f"dl_approve_{idx}_{project_id}_{doc_col}",
                        use_container_width=True,
                        help="❌ File tidak dapat diakses. File mungkin telah dipindah atau dihapus dari server."
                    )
                    st.error(f"⚠️ File tidak ditemukan: `{Path(file_path).name}`")
            
            with col2:
                # Preview button untuk PDF
                if file_ext == '.pdf':
                    preview_key = f'show_preview_{project_id}_{doc_col}_{idx}'
                    current_state = st.session_state.get(preview_key, False)
                    button_label = "❌ Tutup" if current_state else "👁️ Preview"
                    
                    if st.button(button_label, key=f"preview_{idx}_{project_id}_{doc_col}", use_container_width=True):
                        st.session_state[preview_key] = not current_state
                        st.rerun()
            
            with col3:
                if st.button("✅ Setujui", key=f"approve_final_{idx}_{project_id}_{doc_col}", type="primary", use_container_width=True):
                    approve_uploaded_file(project_id, doc_col, file_path, st.session_state['user_id'])
                    st.success(f"✅ Dokumen **{doc_col}** berhasil disetujui!")
                    st.rerun()
            
            with col4:
                if st.button("❌ Tolak", key=f"reject_final_{idx}_{project_id}_{doc_col}", use_container_width=True):
                    reject_uploaded_file(project_id, doc_col, file_path, st.session_state['user_id'])
                    st.warning(f"⚠️ Dokumen **{doc_col}** berhasil ditolak.")
                    st.rerun()
            
            with col5:
                # Opsi pembatalan oleh pengunggah atau Admin/Manager
                cancel_allowed = (uploaded_by == st.session_state['user_id']) or (st.session_state['user_role'] in ['Admin', 'Manager'])
                if cancel_allowed:
                    if st.button("🛑 Batal", key=f"cancel_pending_{idx}_{project_id}_{doc_col}", use_container_width=True):
                        if cancel_pending_file(project_id, doc_col, st.session_state['user_id']):
                            st.success("🛑 Pengajuan dibatalkan.")
                            st.rerun()
            
            # Preview PDF menggunakan PyMuPDF dengan Expander
            preview_key = f'show_preview_{project_id}_{doc_col}_{idx}'
            if st.session_state.get(preview_key, False):
                
                if file_ext == '.pdf':
                    # Cek apakah file ada
                    if not Path(file_path).exists():
                        st.error(f"❌ File tidak ditemukan: {file_path}")
                    else:
                        # Gunakan expander untuk preview yang lebih rapi
                        with st.expander("📄 Preview Dokumen PDF", expanded=True):
                            # Toggle untuk mode tampilan
                            col_opt1, col_opt2 = st.columns([3, 1])
                            with col_opt2:
                                view_mode = st.radio(
                                    "Mode Tampilan",
                                    ["🔲 Grid", "📄 List"],
                                    key=f"view_mode_{project_id}_{doc_col}",
                                    horizontal=True
                                )
                            
                            try:
                                with st.spinner("🔄 Memuat preview PDF..."):
                                    # Render PDF sebagai gambar menggunakan PyMuPDF
                                    images, total_pages = render_pdf_as_images(file_path, max_pages=25, zoom=1.5)
                                    
                                    if images and len(images) > 0:
                                        st.success(f"✅ Berhasil memuat {len(images)} halaman dari total {total_pages} halaman")
                                        st.divider()
                                        
                                        if view_mode == "🔲 Grid":
                                            # Mode Grid - 5 kolom
                                            cols_per_row = 5
                                            num_rows = (len(images) + cols_per_row - 1) // cols_per_row
                                            
                                            for row in range(num_rows):
                                                cols = st.columns(cols_per_row)
                                                
                                                for col_idx in range(cols_per_row):
                                                    img_idx = row * cols_per_row + col_idx
                                                    
                                                    if img_idx < len(images):
                                                        with cols[col_idx]:
                                                            # Card-like container untuk setiap halaman
                                                            st.markdown(f"""
                                                            <div style='text-align: center; 
                                                                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                                                        color: white;
                                                                        padding: 8px; 
                                                                        border-radius: 8px 8px 0 0; 
                                                                        margin-bottom: 0;
                                                                        font-weight: 600;
                                                                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                                                                📄 Halaman {img_idx + 1}
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                            
                                                            # Image dengan border dan shadow
                                                            st.markdown("""
                                                            <style>
                                                            .stImage > img {
                                                                border: 2px solid #e5e7eb;
                                                                border-radius: 0 0 8px 8px;
                                                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                                                            }
                                                            </style>
                                                            """, unsafe_allow_html=True)
                                                            
                                                            st.image(images[img_idx], use_container_width=True)
                                                
                                                # Spacing antar row
                                                if row < num_rows - 1:
                                                    st.markdown("<br>", unsafe_allow_html=True)
                                        
                                        else:
                                            # Mode List - 1 kolom (full width)
                                            for img_idx, img in enumerate(images):
                                                st.markdown(f"""
                                                <div style='text-align: center; 
                                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                                            color: white;
                                                            padding: 12px; 
                                                            border-radius: 10px; 
                                                            margin: 20px 0 10px 0;
                                                            font-weight: 600;
                                                            font-size: 18px;
                                                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                                                    📄 Halaman {img_idx + 1}
                                                </div>
                                                """, unsafe_allow_html=True)
                                                
                                                st.image(img, use_container_width=True)
                                        
                                        # Info jika ada halaman lebih banyak
                                        if total_pages > len(images):
                                            st.divider()
                                            st.info(f"ℹ️ Preview menampilkan {len(images)} halaman pertama. Total dokumen: **{total_pages} halaman**. Download untuk melihat semua halaman.")
                                    
                                    elif total_pages > 0:
                                        st.error(f"❌ Tidak dapat me-render PDF (Total: {total_pages} halaman)")
                                        st.info("💡 File mungkin corrupt atau format tidak didukung. Coba download file.")
                                    else:
                                        st.error("❌ File PDF kosong atau tidak valid")
                                        st.info("💡 Silakan upload ulang file yang valid.")
                                
                            except Exception as e:
                                st.error(f"❌ Tidak dapat menampilkan preview: {str(e)}")
                                st.info("💡 Silakan download file untuk melihat isinya atau upload ulang jika file corrupt.")
                else:
                    with st.expander("ℹ️ Informasi Preview", expanded=True):
                        st.info("Preview hanya tersedia untuk file PDF. Silakan download untuk melihat file lainnya.")
                
                # Separator between documents
                if idx < len(project_docs) - 1:
                    st.markdown("<hr style='margin: 20px 0; border: 1px dashed #e0e0e0;'>", unsafe_allow_html=True)

# --- Tab Dashboard Proyek (dengan sub-tab) ---
def show_dashboard_tab():
    dashboard_subtabs = st.tabs([
        "📈 Ringkasan & Log", 
        "📋 Monitoring Proyek", 
        "📊 Analisis & Laporan"
    ])

    with dashboard_subtabs[0]:
        st.subheader("Ringkasan Dashboard 📊")
        # --- Perhitungan Metrik untuk Stat Card ---
        conn = get_conn()
        total_projects = pd.read_sql_query("SELECT status, created_at FROM projects", conn)
        total_users = pd.read_sql_query("SELECT id, is_approved FROM users", conn)
        audit_logs = pd.read_sql_query("SELECT timestamp, user_id FROM audit_logs", conn)
        conn.close()

        pending_projects_count = total_projects[total_projects['status'] == 'On Progress'].shape[0]
        completed_projects_count = total_projects[total_projects['status'] == 'Done'].shape[0]
        total_users_count = total_users[total_users['is_approved'] == 1].shape[0]
        
        today = datetime.date.today()
        if not audit_logs.empty:
            audit_logs['timestamp'] = pd.to_datetime(audit_logs['timestamp'])
            active_users_today = audit_logs[audit_logs['timestamp'].dt.date == today]['user_id'].nunique()
        else:
            active_users_today = 0

        total_projects['created_at'] = pd.to_datetime(total_projects['created_at'])
        this_month_start = datetime.date.today().replace(day=1)
        last_month_start = (this_month_start - datetime.timedelta(days=1)).replace(day=1)
        
        monthly_projects_count = total_projects[
            (total_projects['created_at'].dt.date >= this_month_start)
        ].shape[0]
        last_month_projects_count = total_projects[
            (total_projects['created_at'].dt.date >= last_month_start) &
            (total_projects['created_at'].dt.date < this_month_start)
        ].shape[0]
        
        if last_month_projects_count > 0:
            monthly_change_percent = ((monthly_projects_count - last_month_projects_count) / last_month_projects_count) * 100
        else:
            monthly_change_percent = 0

        # --- Tampilan Stat Card (Sudah Diperbarui) ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-flex">
                <div>
                  <div class="stat-label">Proyek On Progress</div>
                  <div class="stat-value orange" style="font-size: 32px;">{pending_projects_count}</div>
                  <div class="stat-delta">Belum selesai</div>
                </div>
                <div class="stat-iconbox orange">
                  <svg class="stat-icon orange" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12,6 12,12 16,14"/>
                  </svg>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-flex">
                <div>
                  <div class="stat-label">Proyek Selesai</div>
                  <div class="stat-value green" style="font-size: 32px;">{completed_projects_count}</div>
                  <div class="stat-delta">Status 'Done'</div>
                </div>
                <div class="stat-iconbox green">
                  <svg class="stat-icon green" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22,4 12,14.01 9,11.01"/>
                  </svg>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-flex">
                <div>
                  <div class="stat-label">Total User</div>
                  <div class="stat-value blue" style="font-size: 32px;">{total_users_count}</div>
                  <div class="stat-delta">{active_users_today} aktif hari ini</div>
                </div>
                <div class="stat-iconbox blue">
                  <svg class="stat-icon blue" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="8.5" cy="7" r="4"/>
                    <path d="M20 8v6"/>
                    <path d="M23 11h-6"/>
                  </svg>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            delta_text = f"{monthly_change_percent:.0f}% dari bulan lalu"
            delta_color_class = "stat-delta"
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-flex">
                <div>
                  <div class="stat-label">Proyek Bulan Ini</div>
                  <div class="stat-value purple" style="font-size: 32px;">{monthly_projects_count}</div>
                  <div class="{delta_color_class}">{delta_text}</div>
                </div>
                <div class="stat-iconbox purple">
                  <svg class="stat-icon purple" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        col_deadlines, col_logs = st.columns(2)
        with col_deadlines:
            st.subheader("Tenggat Waktu Proyek Mendekat ⏰")
            deadline_projects = fetchall("SELECT item, part_no, project, project_end_date, customer FROM projects WHERE status IN ('On Progress', 'Hold') AND project_end_date IS NOT NULL ORDER BY project_end_date ASC LIMIT 5")
            
            if deadline_projects:
                deadline_df = pd.DataFrame(deadline_projects)
                st.dataframe(deadline_df,
                column_config={
                    "item": "Item",
                    "part_no": "Part Number",
                    "project": "Nama Proyek",
                    "project_end_date": st.column_config.DateColumn("Batas Waktu", format="DD-MM-YYYY"),
                    "customer": "Customer"
                },
                hide_index=True, use_container_width=True)
            else:
                st.info("Tidak ada proyek dengan batas waktu mendekat.")

        with col_logs:
            st.subheader("Log Aktivitas Terbaru 📜")
            # Gabungkan dengan users untuk mendapatkan full_name
            conn = get_conn()
            all_logs_df = pd.read_sql_query(
                """SELECT al.timestamp, al.action, al.user_id, al.details, u.full_name 
                   FROM audit_logs al 
                   LEFT JOIN users u ON al.user_id = u.id 
                   ORDER BY al.timestamp DESC LIMIT 10""", conn)
            conn.close()
            
            if not all_logs_df.empty:
                log_rows = []
                for _, log in all_logs_df.iterrows():
                    timestamp = pd.to_datetime(log['timestamp']).strftime('%d-%b-%Y %H:%M:%S')
                    user_name = log['full_name'] if pd.notna(log['full_name']) else log['user_id']
                    action = log['action']
                    
                    details_dict = {}
                    try:
                        details_dict = json.loads(log['details'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                    details_str = ""
                    if action == "menambah proyek":
                        details_str = f"Menambah proyek {details_dict.get('project_name')} (item: {details_dict.get('item')})"
                    elif action == "menghapus proyek":
                        details_str = f"Menghapus proyek {details_dict.get('project_name')}"
                    elif action == "mengedit proyek":
                        details_str = f"Mengedit proyek {details_dict.get('project_name')}"
                    elif action == "mendelegasikan dokumen":
                        details_str = f"Mendelegasikan dokumen {details_dict.get('doc_column')} ke {details_dict.get('delegated_to')}"
                    elif action == "menyetujui dokumen":
                        details_str = f"Menyetujui dokumen {details_dict.get('doc_column')}"
                    elif action == "mengunggah file pending":
                        details_str = f"Mengunggah file pending untuk dokumen {details_dict.get('doc_column')}"
                    elif action == "mengupdate status proyek ke Done":
                        details_str = f"Update status proyek {details_dict.get('project_name')} ke Done"
                    elif action == "login berhasil":
                        details_str = "Melakukan login"
                    else:
                        details_str = action
                    
                    log_rows.append({
                        "Tanggal & Waktu": timestamp,
                        "Nama": user_name,
                        "Aksi": action,
                        "Detail": details_str
                    })
                
                log_df = pd.DataFrame(log_rows)
                st.dataframe(log_df, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada log aktivitas yang tercatat.")

    # --- Tab Monitoring Proyek ---
    with dashboard_subtabs[1]:
        st.subheader("Tabel Monitoring Proyek 📋")
        df_display = load_df()
        has_data = not df_display.empty
        
        # Filter Controls
        col1, col2, col3, col4 = st.columns([1,1,2,1])
        
        with col1:
            selected_status = st.selectbox("Filter Status", ["All"] + PROJECT_STATUS)
        with col2:
            selected_pic = st.selectbox("Filter PIC", ["All"] + get_all_pids())
        with col3:
            search_query = st.text_input("🔍 Cari Proyek", placeholder="Masukkan kata kunci...")
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Buat Project Baru", use_container_width=True):
                st.session_state['show_create_project_form'] = True
        
        # Form untuk membuat project baru (jika tidak ketemu di pencarian)
        if st.session_state.get('show_create_project_form', False):
            with st.expander("📝 Buat Project Baru", expanded=True):
                st.info("💡 **Tips**: Gunakan fitur ini jika item/project yang Anda cari belum terdaftar dalam sistem.")
                
                with st.form("create_new_project_form"):
                    st.markdown("### Informasi Project Baru")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_item = st.text_input("📦 Item Name *", placeholder="Contoh: HOUSING ASSY")
                        new_part_no = st.text_input("🔢 Part Number *", placeholder="Contoh: RDBSD-N1234")
                    with col_b:
                        new_customer = st.text_input("🏢 Customer *", placeholder="Contoh: SUZUKI")
                        new_project = st.text_input("📋 Project Name", placeholder="Opsional - otomatis dari Item jika kosong")
                    
                    st.markdown("---")
                    col_submit, col_cancel = st.columns([1, 1])
                    
                    with col_submit:
                        submit_new = st.form_submit_button("✅ Buat Project", use_container_width=True)
                    with col_cancel:
                        cancel_new = st.form_submit_button("❌ Batal", use_container_width=True)
                    
                    if cancel_new:
                        st.session_state['show_create_project_form'] = False
                        st.rerun()
                    
                    if submit_new:
                        if not new_item or not new_part_no or not new_customer:
                            st.error("❌ Item, Part Number, dan Customer wajib diisi!")
                        else:
                            # Auto-generate project name dari item jika tidak diisi
                            final_project_name = new_project.strip() if new_project.strip() else new_item.strip()
                            
                            # Default values untuk field lainnya
                            conn = get_conn()
                            c = conn.cursor()
                            
                            # Get default PIC (first available PID)
                            all_pids = get_all_pids()
                            default_pic = all_pids[0] if all_pids else "PID001"
                            
                            # Get current date
                            today = datetime.date.today().strftime('%d-%m-%Y')
                            
                            # Insert project dengan default values
                            c.execute("""
                                INSERT INTO projects (
                                    project, item, part_no, customer, project_start_date, 
                                    project_end_date, pic, status, created_at, created_by
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                final_project_name,
                                new_item.strip(),
                                new_part_no.strip(),
                                new_customer.strip(),
                                today,  # Start date = today
                                None,   # End date = None (belum ditentukan)
                                default_pic,
                                "On Progress",
                                datetime.datetime.now().isoformat(),
                                st.session_state.get('user_id', 'system')
                            ))
                            
                            new_project_id = c.lastrowid
                            conn.commit()
                            conn.close()
                            
                            # Log audit
                            log_audit(
                                st.session_state.get('user_id', 'system'),
                                "menambah proyek baru (quick create)",
                                {
                                    "project_id": new_project_id,
                                    "project_name": final_project_name,
                                    "item": new_item.strip(),
                                    "part_no": new_part_no.strip(),
                                    "customer": new_customer.strip(),
                                    "pic": default_pic,
                                    "status": "On Progress",
                                    "source": "monitoring_proyek_quick_create"
                                }
                            )
                            
                            st.success(f"""
                            ✅ **Project berhasil dibuat!**
                            
                            📋 **Project**: {final_project_name}  
                            📦 **Item**: {new_item.strip()}  
                            🔢 **Part No**: {new_part_no.strip()}  
                            🏢 **Customer**: {new_customer.strip()}  
                            👤 **PIC**: {default_pic}  
                            📅 **Start Date**: {today}
                            
                            💡 Project sudah ditambahkan ke sistem dengan status **On Progress**.  
                            Anda bisa melengkapi detail lainnya di menu **Kelola Project**.
                            """)
                            
                            st.session_state['show_create_project_form'] = False
                            st.session_state['selected_project'] = new_project_id  # Auto-select project baru
                            
                            time.sleep(2)
                            st.rerun()

        filtered_df = df_display.copy()
        if selected_status != "All":
            filtered_df = filtered_df[filtered_df['STATUS'] == selected_status]
        if selected_pic != "All":
            filtered_df = filtered_df[filtered_df['PIC'] == selected_pic]
        if search_query:
            searchable_cols = filtered_df.columns.tolist()
            mask = filtered_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False).any(), axis=1)
            filtered_df = filtered_df[mask]

        if has_data and not filtered_df.empty:
            # Display total projects
            st.markdown(f"**Menampilkan {len(filtered_df)} proyek**")
            st.markdown("---")
            
            # Inisialisasi session state untuk single selection
            if 'selected_project' not in st.session_state:
                st.session_state['selected_project'] = None
            
            # Buat tabel data untuk ditampilkan
            table_data = []
            for _, row in filtered_df.iterrows():
                # Hitung progress kelengkapan dokumen
                all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
                total_docs = len(all_doc_cols)
                completed_docs = 0
                
                for col_name in all_doc_cols:
                    doc_data = row.get(col_name, {})
                    if col_name in MULTIPLE_FILE_DOCS:
                        if doc_data.get('paths'):
                            completed_docs += 1
                    else:
                        if doc_data.get('path'):
                            completed_docs += 1
                
                progress_percentage = (completed_docs / total_docs * 100) if total_docs > 0 else 0
                
                # Tentukan icon berdasarkan status
                status_icons = {
                    'On Progress': '🔄',
                    'Done': '✅',
                    'Hold': '⏸️',
                    'Canceled': '❌'
                }
                status_icon = status_icons.get(row['STATUS'], '📋')
                
                table_data.append({
                    '✅': row['NO'] == st.session_state['selected_project'],
                    'No': row['NO'],
                    'Status': f"{status_icon} {row['STATUS']}",
                    'Project': row['PROJECT'],
                    'Item': row['ITEM'],
                    'Part No': row['PART NO'],
                    'Customer': row['CUSTOMER'],
                    'PIC': row['PIC'],
                    'Start Date': row.get('PROJECT START DATE', 'N/A'),
                    'End Date': row.get('PROJECT END DATE', 'N/A'),
                    'Progress': f"{completed_docs}/{total_docs} ({progress_percentage:.0f}%)"
                })
            
            # Tampilkan tabel dengan checkbox (single select)
            st.markdown("### 📋 Pilih Proyek untuk Melihat Detail (Pilih Satu)")
            
            # Tampilkan tabel dengan data_editor untuk checkbox interaktif - HANYA KOLOM TERPILIH
            display_df = pd.DataFrame(table_data)
            
            # Hanya tampilkan kolom: Pilih, Status, Item, Part No, Project, Customer, Start Date, End Date, Progress
            columns_to_show = ['✅', 'Status', 'Item', 'Part No', 'Project', 'Customer', 'Start Date', 'End Date', 'Progress']
            display_df_filtered = display_df[columns_to_show]
            
            edited_df = st.data_editor(
                display_df_filtered,
                use_container_width=True,
                hide_index=True,
                disabled=["Status", "Item", "Part No", "Project", "Customer", "Start Date", "End Date", "Progress"],
                column_config={
                    "✅": st.column_config.CheckboxColumn(
                        "Pilih",
                        help="Centang untuk melihat detail proyek (hanya bisa pilih satu)",
                        default=False,
                        width="small"
                    ),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Item": st.column_config.TextColumn("Item", width="medium"),
                    "Part No": st.column_config.TextColumn("Part No", width="medium"),
                    "Project": st.column_config.TextColumn("Project", width="small"),
                    "Customer": st.column_config.TextColumn("Customer", width="small"),
                    "Start Date": st.column_config.TextColumn("Start Date", width="small"),
                    "End Date": st.column_config.TextColumn("End Date", width="small"),
                    "Progress": st.column_config.TextColumn("Progress", width="small")
                },
                key="project_table_editor"
            )
            
            # Update selected project berdasarkan checkbox yang dicentang (hanya satu)
            # Gabungkan dengan data asli untuk mendapatkan 'No'
            edited_df['No'] = display_df['No'].values[:len(edited_df)]
            selected_rows = edited_df[edited_df['✅'] == True]
            if len(selected_rows) > 1:
                # Jika lebih dari satu dipilih, ambil yang terakhir dipilih
                st.session_state['selected_project'] = selected_rows.iloc[-1]['No']
                st.rerun()
            elif len(selected_rows) == 1:
                st.session_state['selected_project'] = selected_rows.iloc[0]['No']
            else:
                st.session_state['selected_project'] = None
            
            # Tampilkan detail proyek yang dipilih
            if st.session_state['selected_project']:
                st.markdown("---")
                
                project_id = st.session_state['selected_project']
                # Cari data proyek
                row = filtered_df[filtered_df['NO'] == project_id].iloc[0] if not filtered_df[filtered_df['NO'] == project_id].empty else None
                
                if row is not None:
                    status_class = row['STATUS'].lower().replace(' ', '-')
                    
                    # Tentukan warna dan icon badge berdasarkan status
                    status_config = {
                        'on-progress': {'color': '#fb923c', 'bg': '#fff7ed', 'icon': '🔄'},
                        'done': {'color': '#22c55e', 'bg': '#f0fdf4', 'icon': '✅'},
                        'hold': {'color': '#94a3b8', 'bg': '#f1f5f9', 'icon': '⏸️'},
                        'canceled': {'color': '#dc2626', 'bg': '#fee2e2', 'icon': '❌'}
                    }
                    status_info = status_config.get(status_class, {'color': '#6366f1', 'bg': '#eff6ff', 'icon': '📋'})
                    
                    # Header card proyek yang lebih rapi dan modern
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 30px; border-radius: 15px; margin-bottom: 25px; 
                                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; gap: 25px;'>
                            <div style='flex: 1;'>
                                <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 20px;'>
                                    <div style='background: rgba(255,255,255,0.2); padding: 10px 14px; border-radius: 10px;'>
                                        <span style='font-size: 24px;'>📦</span>
                                    </div>
                                    <h2 style='margin: 0; color: white; font-size: 26px; font-weight: 700; 
                                                text-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{row['PROJECT']}</h2>
                                </div>
                                <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px 20px;'>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>Item</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row['ITEM']}</p>
                                    </div>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>Part No</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row['PART NO']}</p>
                                    </div>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>Customer</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row['CUSTOMER']}</p>
                                    </div>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>PIC</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row['PIC']}</p>
                                    </div>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>Start Date</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row.get('PROJECT START DATE', 'N/A')}</p>
                                    </div>
                                    <div style='background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 8px;
                                                backdrop-filter: blur(10px);'>
                                        <span style='color: rgba(255,255,255,0.75); font-size: 11px; 
                                                     text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;'>Deadline</span>
                                        <p style='margin: 4px 0 0 0; color: white; font-weight: 600; font-size: 14px;'>{row.get('PROJECT END DATE', 'N/A')}</p>
                                    </div>
                                </div>
                            </div>
                            <div style='min-width: 140px;'>
                                <div style='background: {status_info["bg"]}; 
                                            padding: 14px 22px; border-radius: 12px; 
                                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                                            border: 2px solid {status_info["color"]};
                                            text-align: center;'>
                                    <div style='font-size: 28px; margin-bottom: 5px;'>{status_info["icon"]}</div>
                                    <div style='color: {status_info["color"]}; font-size: 13px; 
                                                font-weight: 700; text-transform: uppercase; 
                                                letter-spacing: 0.5px;'>{row['STATUS']}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
                    
                    # Hitung progress kelengkapan dokumen
                    total_docs = len(all_doc_cols)
                    completed_docs = 0
                    
                    for col_name in all_doc_cols:
                        doc_data = row.get(col_name, {})
                        if col_name in MULTIPLE_FILE_DOCS:
                            # Multiple file doc
                            if doc_data.get('paths'):
                                completed_docs += 1
                        else:
                            # Single file doc
                            if doc_data.get('path'):
                                completed_docs += 1
                    
                    progress_percentage = (completed_docs / total_docs * 100) if total_docs > 0 else 0
                    
                    # Progress card yang lebih menarik dengan warna dinamis
                    progress_color = '#22c55e' if progress_percentage == 100 else '#fb923c' if progress_percentage >= 50 else '#dc2626'
                    
                    # Layout berdampingan: Progress & Tabel Dokumen
                    col_progress, col_status = st.columns([1, 2])
                    
                    with col_progress:
                        # Card Progress dengan height yang sesuai
                        st.markdown(f"""
                        <div style='background: white; padding: 25px 20px; border-radius: 12px; 
                                    box-shadow: 0 2px 12px rgba(0,0,0,0.1); border-left: 6px solid {progress_color};
                                    height: 550px; display: flex; flex-direction: column; justify-content: space-between;'>
                            <div>
                                <h4 style='margin: 0 0 25px 0; color: #1e293b; font-size: 17px; font-weight: 700;'>
                                    📊 Progress Kelengkapan Dokumen
                                </h4>
                                <div style='text-align: center; margin: 30px 0 25px 0;'>
                                    <div style='position: relative; width: 170px; height: 170px; margin: 0 auto;'>
                                        <svg width="170" height="170" style='transform: rotate(-90deg);'>
                                            <circle cx="85" cy="85" r="70" fill="none" stroke="#e5e7eb" stroke-width="14"/>
                                            <circle cx="85" cy="85" r="70" fill="none" stroke="{progress_color}" stroke-width="14"
                                                    stroke-dasharray="{440 * progress_percentage / 100} 440"
                                                    stroke-linecap="round"
                                                    style='transition: stroke-dasharray 0.6s ease;'/>
                                        </svg>
                                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                                                    text-align: center;'>
                                            <div style='font-size: 38px; font-weight: 800; color: {progress_color};
                                                        line-height: 1;'>
                                                {progress_percentage:.0f}%
                                            </div>
                                            <div style='font-size: 13px; color: #64748b; margin-top: 8px; font-weight: 500;'>
                                                {completed_docs} dari {total_docs}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div style='background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f5 100%); 
                                        padding: 18px; border-radius: 10px; margin-top: 15px;
                                        box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);'>
                                <div style='display: flex; justify-content: space-between; align-items: center; 
                                            margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb;'>
                                    <div style='display: flex; align-items: center;'>
                                        <div style='width: 8px; height: 8px; border-radius: 50%; 
                                                    background: #22c55e; margin-right: 8px;'></div>
                                        <span style='color: #475569; font-size: 13px; font-weight: 500;'>Lengkap</span>
                                    </div>
                                    <span style='color: #22c55e; font-weight: 700; font-size: 16px;'>{completed_docs}</span>
                                </div>
                                <div style='display: flex; justify-content: space-between; align-items: center; 
                                            margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb;'>
                                    <div style='display: flex; align-items: center;'>
                                        <div style='width: 8px; height: 8px; border-radius: 50%; 
                                                    background: #fb923c; margin-right: 8px;'></div>
                                        <span style='color: #475569; font-size: 13px; font-weight: 500;'>Belum Selesai</span>
                                    </div>
                                    <span style='color: #fb923c; font-weight: 700; font-size: 16px;'>{total_docs - completed_docs}</span>
                                </div>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <div style='display: flex; align-items: center;'>
                                        <div style='width: 8px; height: 8px; border-radius: 50%; 
                                                    background: #1e293b; margin-right: 8px;'></div>
                                        <span style='color: #475569; font-size: 13px; font-weight: 500;'>Total Dokumen</span>
                                    </div>
                                    <span style='color: #1e293b; font-weight: 700; font-size: 16px;'>{total_docs}</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Auto-complete message di bawah card
                        st.markdown("<br>", unsafe_allow_html=True)
                        if progress_percentage == 100 and row['STATUS'] != 'Done':
                            st.info("ℹ️ Semua dokumen sudah lengkap! Status akan otomatis berubah menjadi 'Done' saat dokumen terakhir di-approve.")
                        elif progress_percentage == 100 and row['STATUS'] == 'Done':
                            st.success("✅ Proyek ini sudah selesai! Semua dokumen lengkap.")
                    
                    with col_status:
                        # Tabel data dokumen langsung tanpa header badge
                        doc_table_data = []
                        for col_name in all_doc_cols:
                            doc_data = row.get(col_name, {})
                            # Cek apakah dokumen multiple file atau single file
                            if col_name in MULTIPLE_FILE_DOCS:
                                doc_status = doc_data['status']
                            else:
                                doc_status = "✅ Lengkap" if doc_data.get("path") else "⏳ Belum Selesai"
                            
                            # Format delegasi dengan lebih rapi
                            delegated = doc_data.get("delegated_to") or "-"
                                
                            doc_table_data.append({
                                "📋 Dokumen": col_name,
                                "Status": doc_status,
                                "👥 PIC": delegated,
                                "📅 Deadline": doc_data.get("end_date") or row.get('PROJECT END DATE', '-')
                            })
                        
                        # Tabel langsung dengan tinggi sesuai progress card
                        st.dataframe(
                            pd.DataFrame(doc_table_data), 
                            use_container_width=True, 
                            hide_index=True,
                            height=550
                        )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Header dengan button Download All
                    col_header, col_download = st.columns([4, 1])
                    
                    with col_header:
                        st.markdown("""
                        <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
                                    padding: 18px 25px; border-radius: 12px; margin-bottom: 20px; 
                                    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);'>
                            <h4 style='margin: 0; color: white;'>📁 Riwayat Unggahan & Download</h4>
                            <p style='margin: 5px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;'>
                                Akses dan unduh dokumen yang telah diunggah • Scroll ke kanan untuk melihat semua tab
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_download:
                        st.markdown("<br>", unsafe_allow_html=True)
                        # Collect all files untuk download
                        import zipfile
                        from io import BytesIO
                        
                        all_files_exist = False
                        zip_buffer = BytesIO()
                        
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for col_name in all_doc_cols:
                                if col_name in MULTIPLE_FILE_DOCS and row[col_name]['paths']:
                                    for file_path in row[col_name]['paths']:
                                        try:
                                            full_path = Path(file_path)
                                            if full_path.exists():
                                                file_data = full_path.read_bytes()
                                                zip_file.writestr(f"{col_name}/{full_path.name}", file_data)
                                                all_files_exist = True
                                        except:
                                            pass
                                elif col_name not in MULTIPLE_FILE_DOCS:
                                    rev_hist = get_revision_history(row['NO'], col_name)
                                    if rev_hist:
                                        valid_revisions = [rev for rev in rev_hist if rev['revision_number'] != -1]
                                        for rev in valid_revisions:
                                            try:
                                                full_path = Path(rev['file_path'])
                                                if full_path.exists():
                                                    file_data = full_path.read_bytes()
                                                    zip_file.writestr(f"{col_name}/Rev{rev['revision_number']}_{full_path.name}", file_data)
                                                    all_files_exist = True
                                            except:
                                                pass
                        
                        if all_files_exist:
                            zip_buffer.seek(0)
                            # Buat nama file dengan format: PartName_PartNumber_Project_Customer_All_Documents.zip
                            part_name = str(row.get('ITEM', '')).replace(' ', '_').replace('/', '-')
                            part_number = str(row.get('PART NO', '')).replace(' ', '_').replace('/', '-')
                            project_name = str(row.get('PROJECT', '')).replace(' ', '_').replace('/', '-')
                            customer_name = str(row.get('CUSTOMER', '')).replace(' ', '_').replace('/', '-')
                            
                            zip_filename = f"{part_name}_{part_number}_{project_name}_{customer_name}_All_Documents.zip"
                            
                            st.download_button(
                                label="📦 Download All",
                                data=zip_buffer.getvalue(),
                                file_name=zip_filename,
                                mime="application/zip",
                                use_container_width=True,
                                type="primary"
                            )
                        else:
                            st.button("📦 Download All", disabled=True, use_container_width=True, help="Tidak ada file tersedia")
                    
                    # Tambahkan custom CSS untuk horizontal scroll pada tabs
                    st.markdown("""
                    <style>
                        /* Horizontal scroll untuk tabs dokumen */
                        div[data-baseweb="tab-list"] {
                            overflow-x: auto !important;
                            overflow-y: hidden !important;
                            white-space: nowrap !important;
                            -webkit-overflow-scrolling: touch !important;
                            scrollbar-width: thin !important;
                            scrollbar-color: #6366f1 #e5e7eb !important;
                        }
                        
                        /* Custom scrollbar untuk browser webkit */
                        div[data-baseweb="tab-list"]::-webkit-scrollbar {
                            height: 8px !important;
                        }
                        
                        div[data-baseweb="tab-list"]::-webkit-scrollbar-track {
                            background: #f1f5f9 !important;
                            border-radius: 10px !important;
                        }
                        
                        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
                            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
                            border-radius: 10px !important;
                        }
                        
                        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb:hover {
                            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
                        }
                        
                        /* Pastikan tabs tidak wrap */
                        div[data-baseweb="tab-list"] button {
                            flex-shrink: 0 !important;
                            min-width: fit-content !important;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Tabs untuk setiap dokumen agar lebih terorganisir
                    doc_tabs = st.tabs(all_doc_cols)
                    
                    for tab_idx, col_name in enumerate(all_doc_cols):
                        with doc_tabs[tab_idx]:
                            # Header dokumen yang lebih menarik
                            st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e5e7eb 100%); 
                                        padding: 15px 20px; border-radius: 10px; margin-bottom: 15px;
                                        border-left: 4px solid #6366f1;'>
                                <h4 style='margin: 0; color: #1e293b;'>📄 {col_name}</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Tampilkan info delegasi jika ada
                            delegated_info = row[col_name].get('delegated_to', 'N/A')
                            start_date_info = row[col_name].get('start_date', 'N/A')
                            end_date_info = row[col_name].get('end_date', 'N/A')
                            
                            if delegated_info and delegated_info != 'N/A' and delegated_info != 'Belum Didelegasikan':
                                st.markdown(f"""
                                <div style='background: #eff6ff; padding: 12px 16px; border-radius: 8px; 
                                            margin-bottom: 15px; border-left: 4px solid #3b82f6;'>
                                    <p style='margin: 0; color: #1e3a8a; font-size: 14px;'>
                                        <strong>👥 Didelegasikan ke:</strong> {delegated_info}<br>
                                        <strong>📅 Periode:</strong> {start_date_info} s/d {end_date_info}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Upload Manual Section
                            with st.expander("📤 Upload File Manual", expanded=False):
                                st.markdown("**Upload file baru untuk dokumen ini**")
                                
                                if col_name in MULTIPLE_FILE_DOCS:
                                    # Multiple files upload
                                    manual_upload_files = st.file_uploader(
                                        f"Pilih file untuk {col_name} (bisa lebih dari 1)",
                                        accept_multiple_files=True,
                                        key=f"manual_upload_{row['NO']}_{col_name}",
                                        help="Pilih satu atau lebih file untuk diunggah"
                                    )
                                    
                                    if manual_upload_files:
                                        if st.button(f"✅ Upload {len(manual_upload_files)} File", key=f"btn_manual_upload_{row['NO']}_{col_name}"):
                                            try:
                                                upload_multiple_files_for_doc(
                                                    row['NO'],
                                                    col_name,
                                                    manual_upload_files,
                                                    st.session_state['user_id']
                                                )
                                                st.success(f"✅ Berhasil upload {len(manual_upload_files)} file untuk {col_name}!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Gagal upload file: {str(e)}")
                                else:
                                    # Single file upload (dengan revision)
                                    manual_upload_file = st.file_uploader(
                                        f"Pilih file untuk {col_name}",
                                        key=f"manual_upload_{row['NO']}_{col_name}",
                                        help="Upload file baru (akan tersimpan sebagai revisi baru)"
                                    )
                                    
                                    if manual_upload_file:
                                        col_btn1, col_btn2 = st.columns([1, 3])
                                        with col_btn1:
                                            if st.button("✅ Upload", key=f"btn_manual_upload_{row['NO']}_{col_name}"):
                                                try:
                                                    # Langsung approve (tanpa pending) untuk upload manual
                                                    project_id = row['NO']
                                                    user_id = st.session_state['user_id']
                                                    
                                                    # Simpan file
                                                    file_ext = Path(manual_upload_file.name).suffix
                                                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                                    safe_filename = f"{col_name.replace(' ', '_').replace('/', '_')}_{timestamp}{file_ext}"
                                                    file_path = FILES_DIR / safe_filename
                                                    
                                                    with open(file_path, "wb") as f:
                                                        f.write(manual_upload_file.getbuffer())
                                                    
                                                    # Update database
                                                    conn = get_conn()
                                                    c = conn.cursor()
                                                    
                                                    col_field = col_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                                                    
                                                    # Get revision number
                                                    c.execute(f"SELECT {col_field}_path FROM projects WHERE id = ?", (project_id,))
                                                    current = c.fetchone()
                                                    
                                                    # Gunakan relative path untuk kompatibilitas intranet
                                                    relative_path = get_relative_path(file_path)
                                                    
                                                    if current and current[0]:
                                                        # Ada file sebelumnya, buat revision
                                                        c.execute("SELECT MAX(revision_number) FROM revision_history WHERE project_id = ? AND doc_column = ?",
                                                                (project_id, col_name))
                                                        max_rev = c.fetchone()[0]
                                                        new_rev = (max_rev or 0) + 1
                                                        
                                                        c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                                                                (project_id, col_name, new_rev, relative_path, datetime.datetime.now().isoformat(), user_id))
                                                    else:
                                                        # File pertama, revision 1
                                                        c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                                                                (project_id, col_name, 1, relative_path, datetime.datetime.now().isoformat(), user_id))
                                                    
                                                    # Update project table
                                                    upload_date = datetime.datetime.now().strftime('%d-%m-%Y')
                                                    c.execute(f"UPDATE projects SET {col_field}_path = ?, {col_field}_date = ? WHERE id = ?",
                                                            (relative_path, upload_date, project_id))
                                                    
                                                    conn.commit()
                                                    conn.close()
                                                    
                                                    log_audit(user_id, "upload file manual", {
                                                        "project_id": int(project_id),  # Convert to int
                                                        "doc_column": col_name,
                                                        "file_name": manual_upload_file.name
                                                    })
                                                    
                                                    st.success(f"✅ Berhasil upload file untuk {col_name}!")
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"❌ Gagal upload file: {str(e)}")
                                        with col_btn2:
                                            st.info(f"📄 {manual_upload_file.name}")
                            
                            st.markdown("---")
                            
                            # Cek apakah dokumen multiple files
                            if col_name in MULTIPLE_FILE_DOCS and row[col_name]['paths']:
                                st.markdown(f"""
                                <div style='background: #f0fdf4; padding: 10px 15px; border-radius: 8px; 
                                            margin-bottom: 15px; border-left: 4px solid #22c55e;'>
                                    <p style='margin: 0; color: #166534; font-weight: 600;'>
                                        ✅ {len(row[col_name]['paths'])} file tersedia
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Display files dalam cards yang lebih rapi
                                for index, file_path in enumerate(row[col_name]['paths']): 
                                    file_name = Path(file_path).name
                                    
                                    try:
                                        full_file_path = Path(file_path)
                                        
                                        # Cek apakah file exists sebelum membaca
                                        if not full_file_path.exists():
                                            st.error(f"❌ File tidak ditemukan: {file_name}")
                                            continue
                                        
                                        if not full_file_path.is_file():
                                            st.error(f"❌ Path bukan file: {file_name}")
                                            continue
                                        
                                        file_data = full_file_path.read_bytes()
                                        
                                        if not file_data:
                                            st.warning(f"⚠️ File kosong: {file_name}")
                                            continue
                                            
                                        file_size = len(file_data) / 1024  # KB
                                        
                                        # File card dengan styling modern
                                        col_file1, col_file2 = st.columns([4, 1])
                                        with col_file1:
                                            st.markdown(f"""
                                            <div style='background: white; padding: 16px 20px; border-radius: 10px; 
                                                        border: 1px solid #e5e7eb; margin-bottom: 12px;
                                                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                                        transition: all 0.3s ease;'>
                                                <div style='display: flex; align-items: center;'>
                                                    <span style='font-size: 24px; margin-right: 12px;'>📎</span>
                                                    <div>
                                                        <p style='margin: 0; font-weight: 600; color: #1e293b; font-size: 14px;'>
                                                            {file_name}
                                                        </p>
                                                        <p style='margin: 4px 0 0 0; font-size: 12px; color: #64748b;'>
                                                            📦 {file_size:.1f} KB • File #{index + 1}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        with col_file2:
                                            st.markdown("<br>", unsafe_allow_html=True)
                                            st.download_button(
                                                label="⬇️ Download",
                                                data=file_data,
                                                file_name=file_name,
                                                key=f"download_multi_{row['NO']}_{col_name.replace(' ', '_')}_{file_name}_{index}",
                                                use_container_width=True
                                            )
                                    except FileNotFoundError:
                                        st.error(f"❌ File tidak ditemukan: **{file_name}**")
                                    except Exception as e:
                                        st.error(f"❌ Gagal membaca file **{file_name}**: {e}")
                            
                            elif col_name not in MULTIPLE_FILE_DOCS:
                                # Single file document dengan revision history
                                rev_hist = get_revision_history(row['NO'], col_name)
                                
                                if rev_hist:
                                    # Filter hanya revisi yang valid (bukan pending)
                                    valid_revisions = [rev for rev in rev_hist if rev['revision_number'] != -1]
                                    
                                    if valid_revisions:
                                        st.markdown(f"""
                                        <div style='background: #f0fdf4; padding: 10px 15px; border-radius: 8px; 
                                                    margin-bottom: 15px; border-left: 4px solid #22c55e;'>
                                            <p style='margin: 0; color: #166534; font-weight: 600;'>
                                                ✅ {len(valid_revisions)} revisi tersedia
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        for rev in valid_revisions:
                                            rev_file_name = Path(rev['file_path']).name
                                            rev_date = rev['timestamp'].split('T')[0]
                                            rev_time = rev['timestamp'].split('T')[1].split('.')[0] if 'T' in rev['timestamp'] else ''
                                            
                                            # Revision card dengan styling modern
                                            col_rev1, col_rev2 = st.columns([4, 1])
                                            with col_rev1:
                                                st.markdown(f"""
                                                <div style='background: white; padding: 16px 20px; border-radius: 10px; 
                                                            border: 1px solid #e5e7eb; margin-bottom: 12px;
                                                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                                                    <div style='display: flex; align-items: start;'>
                                                        <div style='background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                                                                    color: white; padding: 8px 12px; border-radius: 6px;
                                                                    font-weight: 700; font-size: 13px; margin-right: 15px;
                                                                    min-width: 65px; text-align: center;'>
                                                            Rev {rev['revision_number']}
                                                        </div>
                                                        <div style='flex: 1;'>
                                                            <p style='margin: 0; font-weight: 600; color: #1e293b; font-size: 14px;'>
                                                                📄 {rev_file_name}
                                                            </p>
                                                            <p style='margin: 6px 0 0 0; font-size: 12px; color: #64748b;'>
                                                                👤 {rev['uploaded_by']} • 📅 {rev_date} {rev_time}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                            with col_rev2:
                                                st.markdown("<br>", unsafe_allow_html=True)
                                                rev_file_content = get_file_content(rev['file_path'])
                                                if rev_file_content:
                                                    # Buat key unik dengan menambahkan timestamp
                                                    unique_key = f"download_rev_{row['NO']}_{col_name.replace(' ', '_').replace('/', '_')}_{rev['revision_number']}_{rev['timestamp'].replace(':', '').replace('-', '').replace('.', '').replace('T', '')}"
                                                    st.download_button(
                                                        label="⬇️ Download",
                                                        data=rev_file_content,
                                                        file_name=rev_file_name,
                                                        key=unique_key,
                                                        use_container_width=True
                                                    )
                                                else:
                                                    st.error("❌ Error")
                                    else:
                                        # Fallback: Cek apakah ada file di projects table
                                        col_key = col_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                                        current_file_path = row[col_name].get('path')
                                        
                                        if current_file_path:
                                            st.markdown("""
                                            <div style='background: #fff7ed; padding: 10px 15px; border-radius: 8px; 
                                                        margin-bottom: 15px; border-left: 4px solid #fb923c;'>
                                                <p style='margin: 0; color: #9a3412; font-weight: 600;'>
                                                    ⚠️ File tersedia tapi belum ada riwayat revisi tercatat
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            file_name = Path(current_file_path).name
                                            try:
                                                full_file_path = Path(current_file_path)
                                                if full_file_path.exists() and full_file_path.is_file():
                                                    file_data = full_file_path.read_bytes()
                                                    
                                                    if not file_data:
                                                        st.warning(f"⚠️ File kosong: {file_name}")
                                                    else:
                                                        file_size = len(file_data) / 1024  # KB
                                                        
                                                        col_file1, col_file2 = st.columns([4, 1])
                                                        with col_file1:
                                                            st.markdown(f"""
                                                            <div style='background: white; padding: 16px 20px; border-radius: 10px; 
                                                                        border: 1px solid #e5e7eb; margin-bottom: 12px;
                                                                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                                                                <div style='display: flex; align-items: start;'>
                                                                    <div style='background: linear-gradient(135deg, #fb923c 0%, #f97316 100%);
                                                                                color: white; padding: 8px 12px; border-radius: 6px;
                                                                                font-weight: 700; font-size: 13px; margin-right: 15px;
                                                                                min-width: 65px; text-align: center;'>
                                                                        Current
                                                                    </div>
                                                                    <div style='flex: 1;'>
                                                                        <p style='margin: 0; font-weight: 600; color: #1e293b; font-size: 14px;'>
                                                                            📄 {file_name}
                                                                        </p>
                                                                        <p style='margin: 6px 0 0 0; font-size: 12px; color: #64748b;'>
                                                                            📦 {file_size:.1f} KB • Upload Date: {row[col_name].get('date', 'N/A')}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                        with col_file2:
                                                            st.markdown("<br>", unsafe_allow_html=True)
                                                            st.download_button(
                                                                label="⬇️ Download",
                                                                data=file_data,
                                                                file_name=file_name,
                                                                key=f"download_fallback_{row['NO']}_{col_name.replace(' ', '_').replace('/', '_')}_{file_name}",
                                                                use_container_width=True
                                                            )
                                                else:
                                                    st.error(f"❌ File tidak ditemukan: {current_file_path}")
                                            except Exception as e:
                                                st.error(f"❌ Error membaca file: {str(e)}")
                                        else:
                                            st.markdown("""
                                            <div style='background: #fef3c7; padding: 12px 16px; border-radius: 8px; 
                                                        border-left: 4px solid #f59e0b;'>
                                                <p style='margin: 0; color: #92400e;'>
                                                    ℹ️ Tidak ada file tersedia untuk dokumen ini.
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                else:
                                    # Fallback: Cek apakah ada file di projects table
                                    col_key = col_name.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                                    current_file_path = row[col_name].get('path')
                                    
                                    if current_file_path:
                                        st.markdown("""
                                        <div style='background: #fff7ed; padding: 10px 15px; border-radius: 8px; 
                                                    margin-bottom: 15px; border-left: 4px solid #fb923c;'>
                                            <p style='margin: 0; color: #9a3412; font-weight: 600;'>
                                                ⚠️ File tersedia tapi belum ada riwayat revisi tercatat
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        file_name = Path(current_file_path).name
                                        try:
                                            full_file_path = Path(current_file_path)
                                            if full_file_path.exists():
                                                file_data = full_file_path.read_bytes()
                                                file_size = len(file_data) / 1024  # KB
                                                
                                                col_file1, col_file2 = st.columns([4, 1])
                                                with col_file1:
                                                    st.markdown(f"""
                                                    <div style='background: white; padding: 16px 20px; border-radius: 10px; 
                                                                border: 1px solid #e5e7eb; margin-bottom: 12px;
                                                                box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                                                        <div style='display: flex; align-items: start;'>
                                                            <div style='background: linear-gradient(135deg, #fb923c 0%, #f97316 100%);
                                                                        color: white; padding: 8px 12px; border-radius: 6px;
                                                                        font-weight: 700; font-size: 13px; margin-right: 15px;
                                                                        min-width: 65px; text-align: center;'>
                                                                Current
                                                            </div>
                                                            <div style='flex: 1;'>
                                                                <p style='margin: 0; font-weight: 600; color: #1e293b; font-size: 14px;'>
                                                                    📄 {file_name}
                                                                </p>
                                                                <p style='margin: 6px 0 0 0; font-size: 12px; color: #64748b;'>
                                                                    📦 {file_size:.1f} KB • Upload Date: {row[col_name].get('date', 'N/A')}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                                with col_file2:
                                                    st.markdown("<br>", unsafe_allow_html=True)
                                                    st.download_button(
                                                        label="⬇️ Download",
                                                        data=file_data,
                                                        file_name=file_name,
                                                        key=f"download_fallback_norev_{row['NO']}_{col_name.replace(' ', '_').replace('/', '_')}_{file_name}",
                                                        use_container_width=True
                                                    )
                                            else:
                                                st.error(f"❌ File tidak ditemukan: {current_file_path}")
                                        except Exception as e:
                                            st.error(f"❌ Error membaca file: {str(e)}")
                                    else:
                                        st.markdown("""
                                        <div style='background: #fef3c7; padding: 12px 16px; border-radius: 8px; 
                                                    border-left: 4px solid #f59e0b;'>
                                            <p style='margin: 0; color: #92400e;'>
                                                ℹ️ Tidak ada file tersedia untuk dokumen ini.
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                            else:
                                # Multiple file doc tapi belum ada file
                                st.markdown("""
                                <div style='background: #fef3c7; padding: 12px 16px; border-radius: 8px; 
                                            border-left: 4px solid #f59e0b;'>
                                    <p style='margin: 0; color: #92400e;'>
                                        ℹ️ Belum ada file yang diunggah untuk dokumen ini.
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background: #eff6ff; padding: 20px; border-radius: 10px; 
                            text-align: center; border: 2px dashed #3b82f6;'>
                    <p style='margin: 0; color: #1e40af; font-size: 16px; font-weight: 600;'>
                        👆 Pilih satu proyek dari tabel di atas untuk melihat detailnya
                    </p>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.info("Tidak ada proyek yang sesuai dengan kriteria filter.")
    
    # --- Tab Analisis & Laporan ---
    with dashboard_subtabs[2]:
        st.subheader("Analisis & Laporan 📊")
        st.info("Visualisasi data proyek untuk mendapatkan insight yang lebih baik.")
        
        # Contoh data dummy jika database kosong
        conn = get_conn()
        df = pd.read_sql_query("SELECT project, status, customer, pic, created_at, project_end_date FROM projects", conn)
        conn.close()

        if df.empty:
            st.warning("Data kosong, menampilkan contoh grafik dummy.")
            # Data dummy
            data_dummy = {
                'project': ['Proyek A', 'Proyek B', 'Proyek C', 'Proyek D', 'Proyek E'],
                'status': ['On Progress', 'Done', 'On Progress', 'Done', 'On Progress'],
                'customer': ['Customer A', 'Customer B', 'Customer A', 'Customer C', 'Customer A'],
                'pic': ['Wahyudi', 'Tekat Rahayu', 'Wahyudi', 'Harsono', 'Harsono'],
                'created_at': ['2025-08-01', '2025-08-05', '2025-09-01', '2025-09-10', '2025-09-15'],
                'project_end_date': ['2025-10-01', '2025-09-15', '2025-11-01', '2025-10-20', '2025-12-01']
            }
            df = pd.DataFrame(data_dummy)
        
        # Perbaikan: Konversi kolom 'created_at' ke datetime
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['project_end_date'] = pd.to_datetime(df['project_end_date'])
        
        # Atur layout 2x2
        col_chart1, col_chart2 = st.columns(2)
        col_chart3, col_chart4 = st.columns(2)
        
        # --- 1. Tren Status Proyek per Bulan (Grafik Batang) ---
        with col_chart1:
            st.markdown("#### Tren Status Proyek per Bulan")
            
            # Perbaikan utama: pastikan groupby hanya menggunakan kolom tanggal
            df_monthly = df.set_index('created_at').groupby(pd.Grouper(freq='M'))['status'].value_counts().unstack(fill_value=0)
            
            df_monthly.index = df_monthly.index.strftime('%m-%Y')
            
            df_monthly = df_monthly.reset_index().rename(columns={'created_at': 'Bulan'}).melt(id_vars='Bulan', var_name='Status', value_name='Jumlah Proyek')
            
            fig_monthly = px.bar(df_monthly, x='Bulan', y='Jumlah Proyek', color='Status', 
                                 title='Tren Proyek Selesai dan Berlangsung',
                                 labels={'Bulan': 'Bulan', 'Jumlah Proyek': 'Jumlah'},
                                 color_discrete_map={'On Progress': '#ff9100', 'Done': '#28a745', 'Hold': '#6c757d', 'Canceled': '#dc3545'})
            fig_monthly.update_layout(xaxis_title="Bulan", yaxis_title="Jumlah Proyek")
            st.plotly_chart(fig_monthly, use_container_width=True)

        # --- 2. Distribusi Proyek Berdasarkan Customer (Grafik Pie) ---
        with col_chart2:
            st.markdown("#### Distribusi Proyek Berdasarkan Customer")
            df_customer = df['customer'].value_counts().reset_index()
            df_customer.columns = ['Customer', 'Jumlah']
            fig_customer = px.pie(df_customer, values='Jumlah', names='Customer', title='Persentase Proyek per Customer',
                                  hole=.3)
            st.plotly_chart(fig_customer, use_container_width=True)

        # --- 3. Aktivitas Upload Dokumen per User ---
        with col_chart3:
            st.markdown("#### 📤 User Paling Aktif Upload Dokumen")
            
            # Query audit logs untuk menghitung upload per user
            conn = get_conn()
            upload_stats_df = pd.read_sql_query("""
                SELECT 
                    u.full_name,
                    COUNT(*) as total_uploads
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE al.action IN ('mengunggah file', 'auto-upload dokumen (pending approval)', 'mengunggah file pending')
                GROUP BY al.user_id, u.full_name
                ORDER BY total_uploads DESC
            """, conn)
            conn.close()
            
            if not upload_stats_df.empty and len(upload_stats_df) > 0:
                # Ambil top 10 user
                upload_stats_df = upload_stats_df.head(10)
                
                # Ganti NULL dengan user_id jika full_name tidak ada
                upload_stats_df['full_name'] = upload_stats_df['full_name'].fillna('Unknown User')
                
                # Buat bar chart horizontal
                fig_uploads = px.bar(
                    upload_stats_df, 
                    x='total_uploads', 
                    y='full_name',
                    orientation='h',
                    title='Top 10 User dengan Upload Terbanyak',
                    labels={'total_uploads': 'Jumlah Upload', 'full_name': 'User'},
                    color='total_uploads',
                    color_continuous_scale='Blues',
                    text='total_uploads'
                )
                
                fig_uploads.update_traces(textposition='outside')
                fig_uploads.update_layout(
                    yaxis={'categoryorder':'total ascending'},
                    xaxis_title='Jumlah Upload',
                    yaxis_title='User',
                    showlegend=False,
                    height=400
                )
                
                st.plotly_chart(fig_uploads, use_container_width=True)
                
                # Detail upload per user
                with st.expander("📊 Detail Upload per User"):
                    display_df = upload_stats_df.copy()
                    display_df.columns = ['Nama User', 'Total Upload']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("📭 Belum ada data upload untuk ditampilkan.")
            
        # --- 4. Status Tenggat Waktu Proyek (Grafik Garis) ---
        with col_chart4:
            st.markdown("#### Status Tenggat Waktu Proyek")
            df_deadlines = df[['project_end_date', 'status']].copy()
            
            today = pd.to_datetime(datetime.date.today())
            df_deadlines['Status_Tenggat'] = df_deadlines.apply(
                lambda row: 'Lewat Tenggat' if row['status'] != 'Done' and row['project_end_date'] < today else 'Dalam Tenggat', axis=1
            )
            
            df_deadlines['Bulan'] = df_deadlines['project_end_date'].dt.to_period('M').astype(str)
            df_deadline_monthly = df_deadlines.groupby(['Bulan', 'Status_Tenggat']).size().unstack(fill_value=0)
            
            # Perbaikan di sini: mengubah format DataFrame menjadi 'long'
            df_deadline_monthly = df_deadline_monthly.reset_index().melt(
                id_vars='Bulan', var_name='Status_Tenggat', value_name='Jumlah Proyek'
            )
            
            fig_deadline = px.line(df_deadline_monthly, 
                                   x='Bulan', 
                                   y='Jumlah Proyek', 
                                   color='Status_Tenggat',
                                   title='Tren Status Tenggat Waktu Proyek',
                                   labels={'Bulan': 'Batas Waktu Bulan', 'Jumlah Proyek': 'Jumlah Proyek'},
                                   color_discrete_map={'Dalam Tenggat': '#22c55e', 'Lewat Tenggat': '#dc3545'})
            
            fig_deadline.update_layout(yaxis_title="Jumlah Proyek")
            st.plotly_chart(fig_deadline, use_container_width=True)


        st.markdown("---")
        st.subheader("Export Data Proyek")
        st.info("Ekspor semua data proyek ke dalam format Excel untuk analisis lebih lanjut.")
        if st.button('Export ke Excel'):
            export_df = load_df()
            if not export_df.empty:
                rows = []
                all_cols = BASE_COLUMNS + DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
                for _, r in export_df.iterrows():
                    base = {c: r[c] for c in ['NO', 'ITEM', 'PART NO', 'PROJECT', 'CUSTOMER', 'STATUS', 'PIC', 'PROJECT START DATE', 'PROJECT END DATE']}
                    all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
                    for col in all_doc_cols:
                        cell = r.get(col, {})
                        if col in MULTIPLE_FILE_DOCS:
                            base[col + ' - PATHS'] = json.dumps(cell.get('paths'))
                        else:
                            base[col + ' - PATH'] = cell.get('path')
                            base[col + ' - DATE'] = cell.get('date')
                        
                        base[col + ' - DELEGATED_TO'] = cell.get('delegated_to')
                        base[col + ' - START_DATE'] = cell.get('start_date')
                        base[col + ' - END_DATE'] = cell.get('end_date')
                    rows.append(base)
                out_df = pd.DataFrame(rows)
                buf = BytesIO()
                out_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button('Download .xlsx', data=buf, file_name='project_monitor_export.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                st.success("File berhasil diunduh!")
            else:
                st.warning("Tidak ada data untuk diekspor.")

# --- Tab Manajemen Data Proyek ---
def show_management_tab():
    st.markdown("### 🔧 Manajemen Proyek")
    st.info("💡 Kelola seluruh proyek mulai dari penambahan, edit, hingga delegasi dokumen")
    
    project_tabs = st.tabs([
        "➕ Tambah Proyek", 
        "✏️ Edit Proyek", 
        "🗑️ Hapus Proyek", 
        "📤 Delegasi Dokumen"
    ])
    
    with project_tabs[0]:
        add_project_form()
    with project_tabs[1]:
        edit_project_form()
    with project_tabs[2]:
        delete_project_form()
    with project_tabs[3]:
        delegate_doc_form()

# --- Forms untuk Proyek ---
def add_project_form():
    st.markdown("### ➕ Tambah Proyek Baru")
    st.info("💡 **Tips:** Lengkapi informasi proyek dengan detail untuk memudahkan monitoring")
    
    # Tab untuk memilih metode input
    input_method = st.tabs(["📝 Input Manual", "📊 Upload Excel"])
    
    # Tab 1: Upload Excel
    with input_method[1]:
        st.markdown("#### 📊 Upload Proyek dari Excel")
        st.info("💡 **Upload file Excel (.xlsx atau .xls) dengan kolom yang sesuai untuk menambah banyak proyek sekaligus**")
        
        # Template download
        col_template1, col_template2 = st.columns([1, 2])
        with col_template1:
            # Buat template Excel
            template_data = {
                'Item/Nama Produk *': ['Bracket Support', 'Engine Mount'],
                'Part Number *': ['BRK-001-2025', 'ENG-002-2025'],
                'Nama Proyek *': ['New Model 2025', 'Upgrade Model 2025'],
                'Customer *': ['PT Astra International', 'PT Toyota Indonesia'],
                'Status': ['On Progress', 'On Progress'],
                'PIC': ['Wahyudi (Atmo)', 'Tekat Rahayu'],
                'Tanggal Mulai': ['2025-11-04', '2025-11-05'],
                'Target Selesai': ['2025-12-31', '2025-12-31']
            }
            template_df = pd.DataFrame(template_data)
            
            # Convert to Excel
            template_buffer = BytesIO()
            with pd.ExcelWriter(template_buffer, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False, sheet_name='Projects')
            
            st.download_button(
                label="📥 Download Template Excel",
                data=template_buffer.getvalue(),
                file_name="template_proyek.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download template Excel untuk memudahkan input data"
            )
        
        with col_template2:
            st.markdown("""
            **Kolom yang harus ada dalam Excel:**
            - ✅ `Item/Nama Produk *` (Wajib)
            - ✅ `Part Number *` (Wajib)
            - ✅ `Nama Proyek *` (Wajib)
            - ✅ `Customer *` (Wajib)
            - ⚪ `Status` (Opsional, default: On Progress)
            - ⚪ `PIC` (Opsional, default: N/A)
            - ⚪ `Tanggal Mulai` (Opsional, default: hari ini)
            - ⚪ `Target Selesai` (Opsional, default: 30 hari dari hari ini)
            """)
        
        st.markdown("---")
        
        # Upload file
        uploaded_file = st.file_uploader(
            "📁 Pilih file Excel",
            type=['xlsx', 'xls'],
            help="Upload file Excel dengan format sesuai template"
        )
        
        if uploaded_file is not None:
            try:
                # Baca Excel
                df_excel = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File berhasil dibaca! Ditemukan **{len(df_excel)}** baris data.")
                
                # Validasi kolom wajib
                required_cols = ['Item/Nama Produk *', 'Part Number *', 'Nama Proyek *', 'Customer *']
                missing_cols = [col for col in required_cols if col not in df_excel.columns]
                
                if missing_cols:
                    st.error(f"❌ **Kolom wajib tidak ditemukan:** {', '.join(missing_cols)}")
                    st.info("💡 Pastikan file Excel Anda memiliki kolom yang sesuai dengan template.")
                else:
                    # Preview data
                    st.markdown("#### 👁️ Preview Data")
                    st.dataframe(df_excel.head(10), use_container_width=True)
                    
                    if len(df_excel) > 10:
                        st.info(f"📊 Menampilkan 10 baris pertama dari {len(df_excel)} total baris")
                    
                    # Tombol import
                    st.markdown("---")
                    col_import1, col_import2, col_import3 = st.columns([2, 1, 1])
                    
                    with col_import2:
                        if st.button("✅ Import Semua Data", use_container_width=True, type="primary"):
                            success_count = 0
                            error_count = 0
                            skipped_count = 0
                            error_details = []
                            skipped_details = []
                            
                            # Get default values
                            pids = get_all_pids()
                            default_pic = pids[0] if pids else "N/A"
                            
                            # Load existing projects untuk pengecekan duplikat
                            conn = get_conn()
                            existing_projects = pd.read_sql_query(
                                "SELECT item, part_no, project, customer FROM projects", 
                                conn
                            )
                            conn.close()
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, row in df_excel.iterrows():
                                try:
                                    # Ambil data wajib
                                    item = str(row['Item/Nama Produk *']).strip()
                                    part_no = str(row['Part Number *']).strip()
                                    project_name = str(row['Nama Proyek *']).strip()
                                    customer = str(row['Customer *']).strip()
                                    
                                    # Validasi data wajib tidak kosong
                                    if not all([item, part_no, project_name, customer]) or \
                                       any(x in ['nan', 'None', ''] for x in [item, part_no, project_name, customer]):
                                        error_count += 1
                                        error_details.append(f"Baris {idx+2}: Data wajib tidak lengkap")
                                        continue
                                    
                                    # Cek duplikat berdasarkan kombinasi 4 kolom wajib
                                    is_duplicate = (
                                        (existing_projects['item'].str.lower() == item.lower()) &
                                        (existing_projects['part_no'].str.lower() == part_no.lower()) &
                                        (existing_projects['project'].str.lower() == project_name.lower()) &
                                        (existing_projects['customer'].str.lower() == customer.lower())
                                    ).any()
                                    
                                    if is_duplicate:
                                        skipped_count += 1
                                        skipped_details.append(
                                            f"Baris {idx+2}: Proyek sudah ada (Item: {item}, Part: {part_no})"
                                        )
                                        continue
                                    
                                    # Ambil data opsional dengan default
                                    status = str(row.get('Status', 'On Progress')).strip()
                                    if status in ['nan', 'None', '']:
                                        status = 'On Progress'
                                    if status not in PROJECT_STATUS:
                                        status = 'On Progress'
                                    
                                    pic = str(row.get('PIC', default_pic)).strip()
                                    if pic in ['nan', 'None', '']:
                                        pic = default_pic
                                    
                                    # Tanggal
                                    try:
                                        start_date_value = row.get('Tanggal Mulai', datetime.date.today())
                                        if pd.isna(start_date_value):
                                            project_start_date = datetime.date.today()
                                        elif isinstance(start_date_value, str):
                                            # Try both formats: DD-MM-YYYY and YYYY-MM-DD
                                            try:
                                                project_start_date = datetime.datetime.strptime(start_date_value, '%d-%m-%Y').date()
                                            except:
                                                project_start_date = datetime.datetime.strptime(start_date_value, '%Y-%m-%d').date()
                                        else:
                                            project_start_date = pd.to_datetime(start_date_value).date()
                                    except:
                                        project_start_date = datetime.date.today()
                                    
                                    try:
                                        end_date_value = row.get('Target Selesai')
                                        if pd.isna(end_date_value):
                                            project_end_date = datetime.date.today() + datetime.timedelta(days=30)
                                        elif isinstance(end_date_value, str):
                                            # Try both formats: DD-MM-YYYY and YYYY-MM-DD
                                            try:
                                                project_end_date = datetime.datetime.strptime(end_date_value, '%d-%m-%Y').date()
                                            except:
                                                project_end_date = datetime.datetime.strptime(end_date_value, '%Y-%m-%d').date()
                                        else:
                                            project_end_date = pd.to_datetime(end_date_value).date()
                                    except:
                                        project_end_date = datetime.date.today() + datetime.timedelta(days=30)
                                    
                                    # Validasi tanggal
                                    if project_end_date < project_start_date:
                                        project_end_date = project_start_date + datetime.timedelta(days=30)
                                    
                                    # Insert ke database
                                    insert_row(
                                        item, part_no, project_name, customer, status, pic,
                                        project_start_date.strftime('%d-%m-%Y'),
                                        project_end_date.strftime('%d-%m-%Y'),
                                        st.session_state['user_id']
                                    )
                                    success_count += 1
                                    
                                except Exception as e:
                                    error_count += 1
                                    error_details.append(f"Baris {idx+2}: {str(e)}")
                                
                                # Update progress
                                progress = (idx + 1) / len(df_excel)
                                progress_bar.progress(progress)
                                status_text.text(f"Processing... {idx+1}/{len(df_excel)}")
                            
                            # Clear progress
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Tampilkan hasil dengan summary
                            st.markdown("---")
                            st.markdown("### 📊 Hasil Import")
                            
                            col_result1, col_result2, col_result3 = st.columns(3)
                            with col_result1:
                                st.metric("✅ Berhasil", success_count, help="Jumlah proyek yang berhasil diimport")
                            with col_result2:
                                st.metric("⏭️ Dilewati", skipped_count, help="Proyek duplikat yang dilewati")
                            with col_result3:
                                st.metric("❌ Error", error_count, help="Baris yang gagal diimport")
                            
                            # Success message
                            if success_count > 0:
                                st.success(f"✅ **Berhasil mengimport {success_count} proyek baru!**")
                                st.balloons()
                            
                            # Skipped message
                            if skipped_count > 0:
                                st.info(f"ℹ️ **{skipped_count} baris dilewati** karena data sudah ada di database")
                                with st.expander("📋 Detail Data yang Dilewati"):
                                    for skip in skipped_details[:10]:
                                        st.text(f"• {skip}")
                                    if len(skipped_details) > 10:
                                        st.info(f"... dan {len(skipped_details) - 10} data lainnya")
                            
                            # Error message
                            if error_count > 0:
                                st.warning(f"⚠️ **{error_count} baris gagal diimport**")
                                with st.expander("📋 Detail Error"):
                                    for error in error_details[:10]:
                                        st.text(f"• {error}")
                                    if len(error_details) > 10:
                                        st.info(f"... dan {len(error_details) - 10} error lainnya")
                            
                            # Auto refresh jika ada success
                            if success_count > 0:
                                st.info("🔄 Halaman akan refresh otomatis dalam 3 detik...")
                                import time
                                time.sleep(3)
                                st.rerun()
                            elif skipped_count > 0 and error_count == 0:
                                st.warning("⚠️ Semua data sudah ada di database. Tidak ada yang diimport.")
                            elif error_count > 0 and success_count == 0 and skipped_count == 0:
                                st.error("❌ Tidak ada data yang berhasil diimport. Periksa file Excel Anda.")
                    
                    with col_import3:
                        if st.button("❌ Batal", use_container_width=True):
                            st.info("Import dibatalkan")
                            st.rerun()
            
            except Exception as e:
                st.error(f"❌ **Error membaca file Excel:** {str(e)}")
                st.info("💡 Pastikan file Excel Anda dalam format yang benar dan tidak corrupt.")
    
    # Tab 2: Input Manual
    with input_method[0]:
        pids = get_all_pids()
        with st.form(key='add_form'):
            st.markdown("#### 📋 Informasi Dasar Proyek")
            col1, col2 = st.columns(2)
            with col1:
                item = st.text_input(
                    'Item/Nama Produk *',
                    placeholder="Contoh: Bracket Support",
                    help="Masukkan nama item atau produk yang akan dikerjakan"
                )
                project_name = st.text_input(
                    'Nama Proyek *',
                    placeholder="Contoh: New Model 2025",
                    help="Berikan nama proyek yang deskriptif"
                )
            with col2:
                part_no = st.text_input(
                    'Part Number *',
                    placeholder="Contoh: BRK-001-2025",
                    help="Nomor part sesuai dengan sistem perusahaan"
                )
                customer = st.text_input(
                    'Customer *',
                    placeholder="Contoh: PT Astra International",
                    help="Nama customer atau klien proyek"
                )
            
            st.markdown("---")
            st.markdown("#### 👥 Status & Penanggung Jawab")
            col3, col4 = st.columns(2)
            with col3:
                status = st.selectbox(
                    'Status Proyek',
                    PROJECT_STATUS,
                    help="Pilih status awal proyek"
                )
            with col4:
                if pids:
                    pic = st.selectbox(
                        'PIC (Person In Charge)',
                        pids,
                        help="Pilih penanggung jawab utama proyek"
                    )
                else:
                    pic = st.text_input('PIC (Penanggung Jawab)', value="N/A", disabled=True)
            
            st.markdown("---")
            st.markdown("#### 📅 Timeline Proyek")
            col5, col6 = st.columns(2)
            with col5:
                project_start_date = st.date_input(
                    "Tanggal Mulai",
                    value=datetime.date.today(),
                    help="Kapan proyek akan dimulai"
                )
            with col6:
                project_end_date = st.date_input(
                    "Target Selesai *",
                    help="Deadline target penyelesaian proyek"
                )

            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
            with col_btn2:
                submit_button = st.form_submit_button(
                    label='✅ Simpan Proyek',
                    use_container_width=True
                )
            
            if submit_button:
                if not all([item, part_no, project_name, customer, project_end_date]):
                    st.error("⚠️ **Mohon lengkapi semua field yang bertanda (*)** untuk melanjutkan.")
                elif project_end_date < project_start_date:
                    st.error("⚠️ **Tanggal selesai tidak boleh lebih awal dari tanggal mulai.**")
                else:
                    insert_row(item, part_no, project_name, customer, status, pic, project_start_date.strftime('%d-%m-%Y'), project_end_date.strftime('%d-%m-%Y'), st.session_state['user_id'])
                    st.success(f"✅ **Proyek '{project_name}' berhasil ditambahkan!** Anda dapat melihatnya di dashboard.")
                    st.balloons()
                    st.rerun()

def edit_project_form():
    df_view = load_df()
    pids = get_all_pids()
    
    if df_view.empty:
        st.info("Belum ada proyek untuk diedit.")
        return
    
    conn = get_conn()
    projects_df = pd.read_sql_query("SELECT id, project, item, part_no FROM projects", conn)
    conn.close()
    
    # Create dictionary mapping untuk ambil ID
    project_map = {}
    projects_list = []
    for _, row in projects_df.iterrows():
        display_name = f"{row['project']} - {row['item']} - {row['part_no']}"
        project_map[display_name] = row['id']
        projects_list.append(display_name)
    
    choice_str = st.selectbox('Pilih proyek untuk diedit', projects_list)
    
    if choice_str:
        row_id = project_map[choice_str]
        row_data = get_row_details(row_id)
        
        with st.form(key='edit_main_form'):
            item = st.text_input('ITEM', value=row_data.get('item', ''))
            part_no = st.text_input('PART NO', value=row_data.get('part_no', ''))
            project_name = st.text_input('PROJECT', value=row_data.get('project', ''))
            customer = st.text_input('CUSTOMER', value=row_data.get('customer', ''))

            col_status, col_pic = st.columns(2)
            with col_status:
                current_status = row_data.get('status', PROJECT_STATUS[0])
                status = st.selectbox('STATUS', PROJECT_STATUS, index=PROJECT_STATUS.index(current_status))
            with col_pic:
                current_pic = row_data.get('pic', pids[0] if pids else '')
                pic_index = pids.index(current_pic) if current_pic in pids else 0
                pic = st.selectbox('PIC (Penanggung Jawab)', pids, index=pic_index)
            
            col_dates1, col_dates2 = st.columns(2)
            with col_dates1:
                start_date_val = parse_date_string(row_data['project_start_date'])
                project_start_date = st.date_input("Project Start Date", value=start_date_val)
            with col_dates2:
                end_date_val = parse_date_string(row_data['project_end_date'])
                project_end_date = st.date_input("Project End Date", value=end_date_val)

            save_button = st.form_submit_button('Simpan Perubahan Data Dasar')
            if save_button:
                update_row(row_id, item, part_no, project_name, customer, status, pic, project_start_date.strftime('%d-%m-%Y'), project_end_date.strftime('%d-%m-%Y'), st.session_state['user_id'])
                st.success("✅ Proyek berhasil diperbarui!")
                st.rerun()
                
        st.markdown("---")
        st.subheader("Manajemen Dokumen & Persetujuan")
        all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        
        for doc_col in all_doc_cols:
            st.markdown(f"#### {doc_col}")
            key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')

            # Perubahan di sini: Cek apakah dokumen multiple files
            if doc_col in MULTIPLE_FILE_DOCS:
                uploaded_files = st.file_uploader(
                    f"Unggah file baru untuk {doc_col}",
                    accept_multiple_files=True,
                    key=f"ed_up_multi_{row_id}_{key}"
                )

                # Guard untuk mencegah upload berulang pada rerun Streamlit
                session_guard_key = f"guard_multi_{row_id}_{key}"
                files_signature = None
                if uploaded_files:
                    try:
                        files_signature = sorted([f"{uf.name}-{getattr(uf, 'size', 0)}" for uf in uploaded_files])
                    except Exception:
                        files_signature = sorted([uf.name for uf in uploaded_files])

                if uploaded_files and st.session_state.get(session_guard_key) != files_signature:
                    if upload_multiple_files_for_doc(row_id, doc_col, uploaded_files, st.session_state['user_id']):
                        st.session_state[session_guard_key] = files_signature
                        st.success(f"{len(uploaded_files)} file untuk {doc_col} berhasil diunggah!")
                        st.rerun()
                elif uploaded_files:
                    st.info("File yang sama sudah diproses. Pilih file berbeda untuk mengunggah ulang.")

                # Tampilkan daftar file yang sudah ada
                paths_json = row_data.get(f"{key}_paths")
                try:
                    existing_paths = json.loads(paths_json) if paths_json else []
                except json.JSONDecodeError:
                    existing_paths = []

                
                if existing_paths:
                    st.markdown("###### Daftar File Tersedia")
                    delegated_to_user = row_data.get(f"{key}_delegated_to")
                    role = st.session_state.get('user_role')
                    current_name = get_user_by_id(st.session_state['user_id'])['full_name']
                    allowed_delete = (role in ['Admin', 'Manager']) or (delegated_to_user and current_name == delegated_to_user)
                    for idx, path in enumerate(existing_paths):
                        file_name = Path(path).name
                        upload_date = file_name.split('_')[0]
                        col_f1, col_f2 = st.columns([3,1])
                        with col_f1:
                            st.markdown(f"- **{file_name}** (Tanggal: {upload_date})")
                            st.download_button(
                                label=f"Download {file_name}",
                                data=get_file_content(path),
                                file_name=file_name,
                                key=f"mgmt_download_multi_{row_id}_{key}_{idx}"
                            )
                        with col_f2:
                            if allowed_delete:
                                if st.button("Hapus", key=f"del_multi_{row_id}_{key}_{idx}"):
                                    if delete_file_from_multiple_doc(row_id, doc_col, path, st.session_state['user_id']):
                                        st.success("File berhasil dihapus.")
                                        st.rerun()
                        st.markdown("---")
                else:
                    st.info("Tidak ada file tersedia.")
            
            else: # Logika untuk single file
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT file_path, uploaded_by FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1", (row_id, doc_col))
                pending_file = c.fetchone()
                conn.close()
                
                if pending_file:
                    pending_path, uploaded_by = pending_file
                    st.warning(f"Ada file yang menunggu persetujuan dari **{uploaded_by}**.")
                    
                    delegated_to_user = row_data.get(f"{key}_delegated_to")
                    current_user_name = get_user_by_id(st.session_state['user_id'])['full_name']
                    role = st.session_state.get('user_role')
                    
                    # Aksi untuk Approver: Approve atau Tolak
                    if delegated_to_user == current_user_name or role in ['Admin', 'Manager', 'SPV']:
                        col_app1, col_app2 = st.columns(2)
                        with col_app1:
                            if st.button(f"Approve Dokumen '{doc_col}'", key=f"approve_{row_id}_{key}"):
                                approve_uploaded_file(row_id, doc_col, pending_path, st.session_state['user_id'])
                                st.success(f"Dokumen '{doc_col}' berhasil disetujui dan diperbarui!")
                                st.rerun()
                        with col_app2:
                            if st.button(f"Tolak Dokumen '{doc_col}'", key=f"reject_{row_id}_{key}"):
                                reject_uploaded_file(row_id, doc_col, pending_path, st.session_state['user_id'])
                                st.warning(f"Dokumen '{doc_col}' ditolak.")
                                st.rerun()
                    else:
                        st.info(f"Hanya **{delegated_to_user}** atau Admin yang bisa menyetujui dokumen ini.")

                    # Aksi pembatalan oleh pengunggah atau Admin/Manager
                    cancel_allowed = (uploaded_by == st.session_state['user_id']) or (role in ['Admin', 'Manager'])
                    if cancel_allowed:
                        if st.button("🛑 Batalkan Pengajuan", key=f"cancel_{row_id}_{key}"):
                            if cancel_pending_file(row_id, doc_col, st.session_state['user_id']):
                                st.success("Pengajuan dokumen berhasil dibatalkan.")
                                st.rerun()
                
                else:
                    uploaded = st.file_uploader(f"Unggah file baru untuk {doc_col}", key=f"ed_up_{row_id}_{key}")
                    if uploaded:
                        upload_file_and_save_as_pending(row_id, doc_col, uploaded, st.session_state['user_id'])
                        st.success(f"File untuk {doc_col} berhasil diunggah. Menunggu persetujuan.")
                        st.rerun()

def upload_doc_form():
    df_view = load_df()
    user_name = get_user_by_id(st.session_state['user_id'])['full_name']
    
    if df_view.empty:
        st.info("Belum ada proyek untuk dikelola.")
        return
    
    delegated_docs = {}
    project_details = {}
    
    for _, row in df_view.iterrows():
        all_doc_cols = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        for doc_col in all_doc_cols:
            doc_data = row.get(doc_col, {})
            if not isinstance(doc_data, dict):
                continue
                
            delegated_list = doc_data.get("delegated_to_list", []) or []
            
            # Ensure delegated_list is a list
            if not isinstance(delegated_list, list):
                delegated_list = []
            
            # Check if user_name is in the delegated list (case-insensitive comparison)
            user_match = any(user_name.strip().lower() == delegate.strip().lower() for delegate in delegated_list)
            
            if user_match:
                project_info = f"{row['PROJECT']} - {row['ITEM']} - {row['PART NO']}"
                if project_info not in delegated_docs:
                    delegated_docs[project_info] = []
                    project_details[project_info] = {
                        'id': row['NO'],
                        'project': row['PROJECT'],
                        'item': row['ITEM'],
                        'part_no': row['PART NO'],
                        'customer': row['CUSTOMER'],
                        'status': row['STATUS']
                    }
                delegated_docs[project_info].append(doc_col)

    if not delegated_docs:
        st.warning("⚠️ Tidak ada dokumen yang didelegasikan kepada Anda.")
        return

    # Layout 2 Kolom: Kiri untuk Info Proyek, Kanan untuk Grid Dokumen
    col_left, col_right = st.columns([1, 3])
    
    with col_left:
        st.markdown("### 📋 Pilih Proyek")
        
        # Search proyek
        search_project = st.text_input(
            "🔍 Cari Proyek",
            placeholder="Ketik untuk filter...",
            label_visibility="collapsed"
        )
        
        # Filter proyek jika ada search
        filtered_projects = list(delegated_docs.keys())
        if search_project:
            filtered_projects = [p for p in filtered_projects if search_project.lower() in p.lower()]
        
        if not filtered_projects:
            st.warning("Tidak ada proyek yang cocok.")
            st.stop()
        
        selected_project = st.selectbox(
            "Proyek",
            filtered_projects,
            label_visibility="collapsed"
        )
        
        if selected_project:
            # Extract project_id from details
            details = project_details[selected_project]
            project_id = details['id']
            
            # Tampilkan info proyek di sidebar kiri
            st.markdown("---")
            st.markdown("**Info Proyek:**")
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); 
                        padding: 15px; border-radius: 10px; margin: 10px 0;
                        border: 2px solid #cbd5e1;'>
                <p style='margin: 0; font-size: 11px; color: #64748b;'>NAMA PROYEK</p>
                <p style='margin: 2px 0 10px 0; font-size: 15px; font-weight: 600; color: #1e293b;'>{details['project']}</p>
                <p style='margin: 0; font-size: 11px; color: #64748b;'>ITEM</p>
                <p style='margin: 2px 0 10px 0; font-size: 14px; color: #1e293b;'>{details['item']}</p>
                <p style='margin: 0; font-size: 11px; color: #64748b;'>PART NUMBER</p>
                <p style='margin: 2px 0 10px 0; font-size: 13px; color: #1e293b;'>{details['part_no']}</p>
                <p style='margin: 0; font-size: 11px; color: #64748b;'>CUSTOMER</p>
                <p style='margin: 2px 0 10px 0; font-size: 13px; color: #1e293b;'>{details['customer']}</p>
                <p style='margin: 0; font-size: 11px; color: #64748b;'>STATUS</p>
                <p style='margin: 2px 0 0 0; font-size: 13px; font-weight: 600; color: #059669;'>{details['status']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Statistik singkat
            st.markdown("---")
            st.markdown("**📊 Statistik Upload:**")
            total_docs = len(delegated_docs[selected_project])
            row_data = get_row_details(project_id)
            uploaded_count = 0
            
            for doc_col in delegated_docs[selected_project]:
                key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                if doc_col in MULTIPLE_FILE_DOCS:
                    paths_json = row_data.get(f"{key}_paths")
                    try:
                        existing_paths = json.loads(paths_json) if paths_json else []
                        if existing_paths:
                            uploaded_count += 1
                    except:
                        pass
                else:
                    if row_data.get(f"{key}_path"):
                        uploaded_count += 1
            
            st.markdown(f"""
            <div style='background: #ecfdf5; padding: 15px; border-radius: 10px; text-align: center;'>
                <p style='margin: 0; font-size: 24px; font-weight: 700; color: #059669;'>{uploaded_count}/{total_docs}</p>
                <p style='margin: 5px 0 0 0; font-size: 12px; color: #047857;'>Dokumen Terupload</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        if selected_project:
            # Header dengan info proyek
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
                        padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
                <h3 style='margin: 0; color: white;'>📄 Dokumen yang Perlu Diupload</h3>
                <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>
                    📦 <b>{details['item']}</b> | Proyek: <b>{details['project']}</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            row_data = get_row_details(project_id)
            
            # Grid 5 kolom untuk dokumen
            docs_list = delegated_docs[selected_project]
            
            # Buat grid dengan 5 kolom
            for i in range(0, len(docs_list), 5):
                cols = st.columns(5)
                
                for col_idx, col in enumerate(cols):
                    doc_idx = i + col_idx
                    if doc_idx < len(docs_list):
                        doc_col = docs_list[doc_idx]
                        key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                        
                        with col:
                            # Cek status dokumen
                            is_uploaded = False
                            file_count = 0
                            
                            if doc_col in MULTIPLE_FILE_DOCS:
                                paths_json = row_data.get(f"{key}_paths")
                                try:
                                    existing_paths = json.loads(paths_json) if paths_json else []
                                    if existing_paths:
                                        is_uploaded = True
                                        file_count = len(existing_paths)
                                except:
                                    pass
                            else:
                                if row_data.get(f"{key}_path"):
                                    is_uploaded = True
                                    file_count = 1
                                else:
                                    # Cek pending
                                    conn = get_conn()
                                    c = conn.cursor()
                                    c.execute("SELECT file_path FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1", (project_id, doc_col))
                                    pending_file = c.fetchone()
                                    conn.close()
                                    if pending_file:
                                        is_uploaded = "pending"
                            
                            # Status color
                            if is_uploaded == "pending":
                                status_color = "#f59e0b"
                                status_icon = "⏳"
                                status_text = "Pending"
                            elif is_uploaded:
                                status_color = "#22c55e"
                                status_icon = "✅"
                                status_text = f"{file_count} file"
                            else:
                                status_color = "#94a3b8"
                                status_icon = "�"
                                status_text = "Belum"
                            
                            # Card dokumen kecil dengan icon berbeda
                            if is_uploaded == "pending":
                                icon_display = "⏳"
                                border_style = f"2px solid {status_color}"
                            elif is_uploaded:
                                icon_display = "✓"
                                border_style = f"3px solid {status_color}"
                            else:
                                icon_display = "○"
                                border_style = f"2px dashed {status_color}"
                            
                            st.markdown(f"""
                            <div style='background: white; 
                                        border: {border_style}; 
                                        border-radius: 8px; 
                                        padding: 10px; 
                                        margin-bottom: 10px;
                                        min-height: 100px;
                                        display: flex;
                                        flex-direction: column;
                                        justify-content: space-between;'>
                                <div>
                                    <p style='margin: 0; font-size: 24px; text-align: center; font-weight: bold;'>{icon_display}</p>
                                    <p style='margin: 5px 0; font-size: 11px; font-weight: 600; 
                                              color: #1e293b; text-align: center; line-height: 1.2;'>{doc_col}</p>
                                </div>
                                <div style='background: {status_color}; 
                                           padding: 4px; border-radius: 4px; text-align: center;'>
                                    <p style='margin: 0; font-size: 9px; color: white; font-weight: 600;'>{status_text}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Expander untuk upload
                            with st.expander("📤 Upload", expanded=False):
                                if doc_col in MULTIPLE_FILE_DOCS:
                                    # Multiple Files
                                    st.caption("📁 Multiple Files")
                                    
                                    uploaded_files = st.file_uploader(
                                        "Pilih file",
                                        accept_multiple_files=True,
                                        key=f"upload_multi_{project_id}_{key}",
                                        label_visibility="collapsed"
                                    )
                                    
                                    guard_doc_key = key
                                    session_guard_key = f"guard_multi_{project_id}_{guard_doc_key}"
                                    
                                    if uploaded_files:
                                        try:
                                            files_signature = sorted([f"{uf.name}-{getattr(uf, 'size', 0)}" for uf in uploaded_files])
                                        except:
                                            files_signature = sorted([uf.name for uf in uploaded_files])
                                        
                                        if st.session_state.get(session_guard_key) != files_signature:
                                            if upload_multiple_files_for_doc(project_id, doc_col, uploaded_files, st.session_state['user_id']):
                                                st.session_state[session_guard_key] = files_signature
                                                st.success("✅ Sukses!")
                                                st.rerun()
                                        else:
                                            st.warning("⚠️ Sudah diupload")
                                    
                                    # List files
                                    paths_json = row_data.get(f"{key}_paths")
                                    try:
                                        existing_paths = json.loads(paths_json) if paths_json else []
                                    except:
                                        existing_paths = []
                                    
                                    if existing_paths:
                                        st.caption(f"📁 {len(existing_paths)} file")
                                        role = st.session_state.get('user_role')
                                        current_name = get_user_by_id(st.session_state['user_id'])['full_name']
                                        delegated_to_user = row_data.get(f"{key}_delegated_to")
                                        allowed_delete = (role in ['Admin','Manager']) or (delegated_to_user and current_name == delegated_to_user)
                                        
                                        for idx, path in enumerate(existing_paths):
                                            file_name = Path(path).name
                                            st.caption(f"{idx+1}. {file_name[:15]}...")
                                            col_d1, col_d2 = st.columns(2)
                                            with col_d1:
                                                st.download_button(
                                                    "⬇️",
                                                    data=get_file_content(path),
                                                    file_name=file_name,
                                                    key=f"dl_multi_{project_id}_{key}_{idx}"
                                                )
                                            with col_d2:
                                                if allowed_delete:
                                                    if st.button("🗑️", key=f"del_multi_{project_id}_{key}_{idx}"):
                                                        if delete_file_from_multiple_doc(project_id, doc_col, path, st.session_state['user_id']):
                                                            st.rerun()
                                else:
                                    # Single File
                                    st.caption("📄 Single File")
                                    
                                    conn = get_conn()
                                    c = conn.cursor()
                                    c.execute("SELECT file_path FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = -1", (project_id, doc_col))
                                    pending_file = c.fetchone()
                                    conn.close()
                                    
                                    if pending_file:
                                        st.warning("⏳ Pending")
                                        if st.button("🛑 Batal", key=f"cancel_{project_id}_{key}"):
                                            if cancel_pending_file(project_id, doc_col, st.session_state['user_id']):
                                                st.rerun()
                                    else:
                                        uploaded_file = st.file_uploader(
                                            "File",
                                            key=f"upload_doc_{project_id}_{key}",
                                            label_visibility="collapsed"
                                        )
                                        if uploaded_file:
                                            upload_file_and_save_as_pending(project_id, doc_col, uploaded_file, st.session_state['user_id'])
                                            st.success("✅")
                                            st.rerun()
        else:
            st.info("👈 Pilih proyek di sebelah kiri")

def delete_project_form():
    df_view = load_df()
    if df_view.empty:
        st.info("Belum ada proyek untuk dihapus.")
        return
    
    # Create dictionary mapping untuk ambil ID
    project_map = {}
    projects_list = []
    for _, row in df_view.iterrows():
        display_name = f"{row['PROJECT']} - {row['ITEM']} - {row['PART NO']}"
        project_map[display_name] = row['NO']
        projects_list.append(display_name)
    
    choice_str = st.selectbox('Pilih proyek untuk dihapus', projects_list)
    if choice_str:
        choice = project_map[choice_str]
        st.warning(f"⚠️ Anda akan menghapus: **{choice_str}**")
        if st.button('Hapus Proyek', help="Aksi ini tidak bisa dibatalkan."):
            delete_row(choice, st.session_state['user_id'])
            st.success("✅ Proyek berhasil dihapus!")
            st.rerun()
            
def delegate_doc_form():
    df_view = load_df()
    pids = get_all_pids()
    current_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()

    if df_view.empty:
        st.info("Belum ada proyek untuk dikelola.")
        return

    st.subheader("Delegasi Dokumen")
    projects_df = load_df()
    
    # Create dictionary mapping untuk ambil ID
    project_map = {}
    projects_list = []
    for _, row in projects_df.iterrows():
        display_name = f"{row['PROJECT']} - {row['ITEM']} - {row['PART NO']}"
        project_map[display_name] = row['NO']
        projects_list.append(display_name)
    
    choice_str = st.selectbox('Pilih proyek untuk delegasi', projects_list)

    if choice_str:
        row_id = project_map[choice_str]
        row_data = get_row_details(row_id)
        st.markdown(f"**Proyek:** {row_data['project']} | **Item:** {row_data['item']} | **Part No:** {row_data['part_no']}")
        st.markdown("---")

        with st.form(key=f"delegate_form_{row_id}"):
            for doc_col in current_docs:
                key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                existing_delegated = row_data.get(f"{key}_delegated_to", None)
                existing_start = row_data.get(f"{key}_start_date", row_data.get('project_start_date'))
                existing_end = row_data.get(f"{key}_end_date", row_data.get('project_end_date'))
                
                st.markdown(f"##### {doc_col}")
                
                col_del, col_start, col_end = st.columns(3)
                
                with col_del:
                    # Multiselect delegasi
                    existing_list_json = row_data.get(f"{key}_delegated_to_list")
                    try:
                        existing_list = json.loads(existing_list_json) if existing_list_json else ([] if not existing_delegated else [existing_delegated])
                    except json.JSONDecodeError:
                        existing_list = ([] if not existing_delegated else [existing_delegated])
                    delegated_to = st.multiselect(
                        "Didelegasikan ke",
                        pids,
                        default=[p for p in existing_list if p in pids],
                        key=f"del_{row_id}_{key}"
                    )
                with col_start:
                    start_date_val = parse_date_string(existing_start)
                    start_date = st.date_input("Tanggal Mulai", value=start_date_val, key=f"start_{row_id}_{key}")
                with col_end:
                    end_date_val = parse_date_string(existing_end)
                    end_date = st.date_input("Tanggal Selesai", value=end_date_val, key=f"end_{row_id}_{key}")
            
            submit_button = st.form_submit_button("Simpan Delegasi")

            if submit_button:
                for doc_col in current_docs:
                    key = doc_col.replace(' ', '_').replace('/', '_').replace('.', '').replace('-', '_')
                    delegated_to = st.session_state[f"del_{row_id}_{key}"]
                    start_date = st.session_state[f"start_{row_id}_{key}"]
                    end_date = st.session_state[f"end_{row_id}_{key}"]

                    final_delegated = delegated_to if delegated_to else None
                    final_start = start_date.strftime('%d-%m-%Y') if start_date else None
                    final_end = end_date.strftime('%d-%m-%Y') if end_date else None
                    
                    update_row_delegation(row_id, doc_col, final_delegated, final_start, final_end, st.session_state['user_id'])
                
                st.success("✅ Delegasi berhasil disimpan!")
                st.rerun()

# --- Manajemen Pengguna (khusus Admin) ---
def manage_users_page():
    st.markdown("""
    <div style='background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); 
                padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: white;'>👥 Kelola Pengguna</h2>
        <p style='margin: 8px 0 0 0; opacity: 0.95;'>Manage user access, roles, dan approval</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tab untuk berbagai fungsi manajemen user
    user_tabs = st.tabs(["➕ Tambah User", "📋 Daftar User", "✅ Approve User", "⚙️ Edit User"])
    
    # Tab 1: Tambah User Baru
    with user_tabs[0]:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                    padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
            <h3 style='margin: 0; color: white;'>➕ Tambah Pengguna Baru</h3>
            <p style='margin: 5px 0 0 0; opacity: 0.9;'>Registrasi user baru langsung oleh Admin</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("add_user_form", clear_on_submit=True):
            st.markdown("#### 📝 Data Pengguna")
            
            col1, col2 = st.columns(2)
            with col1:
                new_user_id = st.text_input("ID Karyawan *", placeholder="Contoh: 1234", help="NIK atau ID unik karyawan")
                new_full_name = st.text_input("Nama Lengkap *", placeholder="Contoh: John Doe")
                new_department = st.text_input("Departemen *", placeholder="Contoh: Production Machining")
            
            with col2:
                new_section = st.text_input("Seksi *", placeholder="Contoh: Mc Engineering")
                new_role = st.selectbox("Role *", ROLES, help="Pilih role/jabatan user")
                new_password = st.text_input("Password *", type="password", placeholder="Min. 3 karakter")
            
            col_auto1, col_auto2 = st.columns([1, 3])
            with col_auto1:
                auto_approve = st.checkbox("Auto Approve", value=True, help="Langsung approve user setelah registrasi")
            
            st.markdown("---")
            col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 2])
            with col_submit1:
                submitted = st.form_submit_button("➕ Tambah User", use_container_width=True, type="primary")
            with col_submit2:
                st.form_submit_button("🔄 Reset", use_container_width=True)
            
            if submitted:
                # Validasi input
                if not all([new_user_id, new_full_name, new_department, new_section, new_password]):
                    st.error("❌ Semua field wajib diisi!")
                elif len(new_password) < 3:
                    st.error("❌ Password minimal 3 karakter!")
                else:
                    # Cek apakah user ID sudah ada
                    existing_user = get_user_by_id(new_user_id)
                    if existing_user:
                        st.error(f"❌ User dengan ID **{new_user_id}** sudah terdaftar!")
                    else:
                        try:
                            # Register user baru
                            result = register_user(new_user_id, new_password, new_full_name, new_department, new_section)
                            
                            if result:
                                # Update role jika bukan Staff (default) - SEBELUM approve
                                if new_role != "Staff":
                                    update_user_role(new_user_id, new_role, st.session_state['user_id'])
                                
                                # Auto approve jika dipilih
                                if auto_approve:
                                    approve_user(new_user_id, st.session_state['user_id'])
                                    st.success(f"✅ User **{new_full_name}** ({new_user_id}) berhasil ditambahkan dan disetujui!")
                                    st.info(f"📋 Role: **{new_role}** | Status: **Approved**")
                                else:
                                    st.success(f"✅ User **{new_full_name}** ({new_user_id}) berhasil ditambahkan! Menunggu approval.")
                                    st.info(f"📋 Role: **{new_role}** | Status: **Pending Approval**")
                                
                                st.balloons()
                                
                                # Verifikasi data tersimpan
                                verify_user = get_user_by_id(new_user_id)
                                if verify_user:
                                    st.success("✅ Data berhasil tersimpan di database!")
                                else:
                                    st.error("⚠️ Warning: Data mungkin tidak tersimpan dengan benar")
                                
                                # Auto rerun untuk refresh data
                                import time
                                time.sleep(2)  # Delay 2 detik untuk melihat balloons dan message
                                st.rerun()
                            else:
                                st.error("❌ Gagal menambahkan user. ID mungkin sudah digunakan.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            import traceback
                            st.error(f"Debug: {traceback.format_exc()}")
        
        # Info tambahan
        st.markdown("---")
        with st.expander("ℹ️ Informasi Role"):
            st.markdown("""
            **Role dalam sistem:**
            - **Admin**: Full access ke semua fitur, manage users, dan dokumen
            - **Manager**: Approve dokumen, manage proyek, view audit log
            - **SPV**: Approve dokumen yang didelegasikan, manage proyek dalam scope
            - **Staff**: Upload dokumen, view dashboard
            """)
    
    # Tab 2: Daftar User
    with user_tabs[1]:
        # Load data users fresh
        users_df = get_all_users()
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            # Statistik User
            total_users = len(users_df)
            approved_users = len(users_df[users_df['is_approved'] == 1])
            pending_users_count = len(users_df[users_df['is_approved'] == 0])
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Users", total_users, help="Total pengguna terdaftar")
        with col_stat2:
            st.metric("Approved", approved_users, help="User yang sudah disetujui")
        with col_stat3:
            st.metric("Pending", pending_users_count, delta="Need Action" if pending_users_count > 0 else None, help="User menunggu approval")
        
            st.markdown("---")
            st.markdown("### 📋 Daftar Semua Pengguna")
            st.dataframe(users_df, use_container_width=True, hide_index=True)
    
    # Tab 3: Approve User
    with user_tabs[2]:
        # Load data users fresh
        users_df = get_all_users()
        
        st.markdown("### ✅ Setujui Pengguna Baru")
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            pending_users = users_df[users_df['is_approved'] == 0]
            if not pending_users.empty:
                st.warning(f"⚠️ Ada {len(pending_users)} pengguna yang menunggu persetujuan!")
                
                col_approve1, col_approve2 = st.columns([2, 1])
                with col_approve1:
                    user_to_approve = st.selectbox(
                        "Pilih pengguna untuk disetujui",
                        pending_users['id'].tolist(),
                        format_func=lambda x: f"{x} - {pending_users[pending_users['id']==x]['full_name'].iloc[0]}"
                    )
                with col_approve2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✅ Approve User", use_container_width=True):
                        approve_user(user_to_approve, st.session_state['user_id'])
                        st.success(f"✅ Pengguna **{user_to_approve}** berhasil disetujui!")
                        st.rerun()
            else:
                st.success("✅ Semua pengguna sudah disetujui!")
    
    # Tab 4: Edit User
    with user_tabs[3]:
        # Load data users fresh
        users_df = get_all_users()
        
        if users_df.empty:
            st.info("📭 Belum ada pengguna terdaftar dalam sistem.")
        else:
            st.markdown("### ⚙️ Ubah Role & Password Pengguna")
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                user_to_edit = st.selectbox(
                    "Pilih pengguna untuk di-edit",
                    users_df['id'].tolist(),
                    format_func=lambda x: f"{x} - {users_df[users_df['id']==x]['full_name'].iloc[0]}"
                )
            
            if user_to_edit:
                with col_edit2:
                    current_role = users_df[users_df['id'] == user_to_edit]['role'].iloc[0]
                    st.info(f"**Role saat ini:** {current_role}")
                
                st.markdown("---")
                st.markdown("#### 🔄 Ubah Role")
                col_role1, col_role2 = st.columns([2, 1])
                with col_role1:
                    new_role = st.selectbox("Pilih Role Baru", ROLES, index=ROLES.index(current_role))
                with col_role2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Simpan Role", use_container_width=True):
                        update_user_role(user_to_edit, new_role, st.session_state['user_id'])
                        st.success(f"✅ Role pengguna **{user_to_edit}** berhasil diubah menjadi **{new_role}**!")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 🔐 Reset Password")
                new_password = st.text_input(f"Password Baru untuk {user_to_edit}", type="password", key=f"new_pass_{user_to_edit}", placeholder="Min. 3 karakter")
                if st.button("🔄 Reset Password", type="primary"):
                    if new_password:
                        if len(new_password) < 3:
                            st.error("❌ Password minimal 3 karakter!")
                        else:
                            reset_user_password(user_to_edit, new_password, st.session_state['user_id'])
                            st.success(f"✅ Password pengguna {user_to_edit} berhasil direset.")
                            st.rerun()
                    else:
                        st.warning("⚠️ Password baru tidak boleh kosong.")

# --- Auto-detect Document Functions ---
def calculate_similarity(str1, str2):
    """Calculate similarity percentage between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.upper(), str2.upper()).ratio() * 100

def extract_doc_info_from_filename(filename):
    """
    Extract document type, part name, and part number from filename
    Example: "FMEA ENGINE BRACKET YHA (062A) BS-062A-2 Rev.0.pdf"
    Returns: {
        'doc_type': 'FMEA',
        'part_name': 'ENGINE BRACKET YHA (062A)',
        'part_number': 'BS-062A-2'
    }
    """
    # Remove file extension
    name_without_ext = re.sub(r'\.[^.]+$', '', filename)
    
    # List of known document types
    all_doc_types = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
    
    # Try to find document type at the beginning of filename
    doc_type_found = None
    for doc_type in all_doc_types:
        # Check if filename starts with this doc type
        if name_without_ext.upper().startswith(doc_type.upper()):
            doc_type_found = doc_type
            # Remove doc type from filename
            name_without_ext = name_without_ext[len(doc_type):].strip()
            break
    
    if not doc_type_found:
        return None
    
    # Remove common suffixes like "Rev.0", "Rev 1", etc.
    name_without_ext = re.sub(r'\s+Rev\.?\s*\d+', '', name_without_ext, flags=re.IGNORECASE)
    name_without_ext = re.sub(r'\s+Revision\.?\s*\d+', '', name_without_ext, flags=re.IGNORECASE)
    
    # Try to split by common part number patterns
    # Part numbers usually contain alphanumeric with dashes/underscores
    # Pattern: BS-062A-2, 062A-2, Y4L, RDBSD-N, etc.
    parts = name_without_ext.strip().split()
    
    # Try to identify part number (usually the last significant alphanumeric segment before REV)
    part_number = ""
    part_name = ""
    
    # Look for part number pattern (contains dash, underscore, or specific code patterns)
    # Part number patterns:
    # 1. Contains dash/underscore: BS-062A-2, RDBSD-N
    # 2. Short alphanumeric codes: Y4L, 0W010, KVB (usually 3-6 chars)
    # 3. Mix of letters and numbers: 012, 55311-52500-XD1
    
    found_part_number = False
    for i in range(len(parts) - 1, -1, -1):
        part = parts[i]
        
        # Pattern 1: Contains dash or underscore
        if re.search(r'[A-Z0-9]+-[A-Z0-9]+', part, re.IGNORECASE) or re.search(r'[A-Z0-9]+_[A-Z0-9]+', part, re.IGNORECASE):
            part_number = part
            part_name = ' '.join(parts[:i]).strip()
            found_part_number = True
            break
        
        # Pattern 2: Short alphanumeric (3-6 chars, mix of letters and numbers)
        if 3 <= len(part) <= 6 and re.search(r'[A-Z]', part, re.IGNORECASE) and re.search(r'\d', part):
            # Likely a part number code like Y4L, 0W010
            part_number = part
            part_name = ' '.join(parts[:i]).strip()
            found_part_number = True
            break
    
    # If no clear part number found, use all remaining text as part name
    if not found_part_number:
        part_name = ' '.join(parts).strip()
        part_number = ""  # Empty part number is OK
    
    return {
        'doc_type': doc_type_found,
        'part_name': part_name or "",
        'part_number': part_number or ""
    }

def find_matching_project(part_name, part_number, min_similarity=80, return_all_matches=False):
    """
    Find project in database that matches the part name and part number
    with minimum similarity percentage.
    
    Args:
        part_name: The part name extracted from filename
        part_number: The part number extracted from filename (can be empty)
        min_similarity: Minimum similarity threshold (default 80%)
        return_all_matches: If True, returns all matches sorted by similarity (for prioritization)
    
    Returns:
        If return_all_matches=False: Single best match dict or None
        If return_all_matches=True: List of all matches sorted by similarity (highest first)
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, item, part_no, project, customer FROM projects")
    projects = c.fetchall()
    conn.close()
    
    all_matches = []
    
    for project in projects:
        project_id, item, part_no, project_name, customer = project
        
        # Calculate similarity for item (always done)
        item_similarity = calculate_similarity(part_name, item or "")
        
        # Calculate similarity for part_no (only if both exist)
        if part_number and part_no:
            part_no_similarity = calculate_similarity(part_number, part_no)
            # Weighted average: item 60%, part_no 40%
            avg_similarity = (item_similarity * 0.6) + (part_no_similarity * 0.4)
        elif part_number and not part_no:
            # File has part number but project doesn't - use item only
            avg_similarity = item_similarity
            part_no_similarity = 0
        elif not part_number and part_no:
            # Project has part number but file doesn't - use item only
            avg_similarity = item_similarity
            part_no_similarity = 0
        else:
            # Neither has part number - use item only
            avg_similarity = item_similarity
            part_no_similarity = 0
        
        if avg_similarity >= min_similarity:
            all_matches.append({
                'project_id': project_id,
                'item': item,
                'part_no': part_no,
                'project_name': project_name,
                'customer': customer,
                'similarity': avg_similarity,
                'item_similarity': item_similarity,
                'part_no_similarity': part_no_similarity
            })
    
    # Sort by similarity (highest first)
    all_matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    if return_all_matches:
        return all_matches
    else:
        return all_matches[0] if all_matches else None

def auto_upload_document(uploaded_file, doc_type, project_id, user_id, require_approval=True):
    """
    Auto upload document to the specified project and document type
    
    Args:
        uploaded_file: The uploaded file object
        doc_type: Type of document (FMEA, PIS, etc.)
        project_id: Target project ID
        user_id: User who uploaded the file
        require_approval: If True, file will be saved as pending (-1 revision) and require approval
    """
    try:
        # Reset file pointer to beginning
        uploaded_file.seek(0)
        
        # All documents now require approval (both single and multiple)
        conn = get_conn()
        c = conn.cursor()
        
        # Fetch project details for logging
        c.execute("SELECT project, item, part_no FROM projects WHERE id = ?", (project_id,))
        proj_row = c.fetchone()
        project_name = proj_row[0] if proj_row else None
        item = proj_row[1] if proj_row else None
        part_no = proj_row[2] if proj_row else None
        
        # Save file to temporary pending location
        dest_dir = FILES_DIR / f"project_{project_id}" / doc_type.replace(' ', '_')
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = uploaded_file.name
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_path = dest_dir / f"pending_{timestamp}_{safe_name}"
        
        # Reset file pointer before reading
        uploaded_file.seek(0)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(uploaded_file, f)
        
        # Verify file was created
        if not dest_path.exists():
            raise Exception(f"File was not saved to {dest_path}")
        
        if require_approval:
            # Save as pending (revision_number = -1) - requires approval for ALL document types
            timestamp_now = datetime.datetime.now().isoformat()
            # Gunakan relative path untuk kompatibilitas intranet
            relative_path = get_relative_path(dest_path)
            c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by, upload_source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (project_id, doc_type, -1, relative_path, timestamp_now, user_id, "auto_upload"))
            
            conn.commit()
            conn.close()
            
            # Log the action
            log_audit(user_id, "auto-upload dokumen (pending approval)", {
                "project_id": int(project_id),
                "project_name": project_name,
                "item": item,
                "part_no": part_no,
                "doc_column": doc_type,
                "file_name": safe_name,
                "file_path": str(dest_path),
                "status": "pending_approval",
                "source": "auto_upload",
                "is_multiple_file_doc": doc_type in MULTIPLE_FILE_DOCS
            })
            
            st.info(f"📤 File saved as PENDING: {safe_name} for project #{project_id} - {doc_type} (Requires approval)")
            
        else:
                # Direct approval (old behavior) - create revision directly
                c.execute("SELECT MAX(revision_number) FROM revision_history WHERE project_id = ? AND doc_column = ?", (project_id, doc_type))
                max_rev = c.fetchone()[0]
                c.execute("SELECT MAX(revision_number) FROM revision_history WHERE project_id = ? AND doc_column = ?", (project_id, doc_type))
                max_rev = c.fetchone()[0]
                new_rev = (max_rev or 0) + 1
                
                # Update revision_history - gunakan relative path
                timestamp_now = datetime.datetime.now().isoformat()
                relative_path = get_relative_path(dest_path)
                c.execute("INSERT INTO revision_history (project_id, doc_column, revision_number, file_path, timestamp, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                          (project_id, doc_type, new_rev, relative_path, timestamp_now, user_id))
                
                # Verify insertion
                c.execute("SELECT COUNT(*) FROM revision_history WHERE project_id = ? AND doc_column = ? AND revision_number = ?", 
                         (project_id, doc_type, new_rev))
                count = c.fetchone()[0]
                if count == 0:
                    raise Exception(f"Failed to insert revision history for {doc_type}")
                
                # Update projects table - gunakan relative path
                sql = f"UPDATE projects SET {key}_path = ?, {key}_date = ? WHERE id = ?"
                c.execute(sql, (relative_path, datetime.date.today().strftime('%d-%m-%Y'), project_id))
                
                conn.commit()
                conn.close()
                
                # Debug info
                st.info(f"✅ File saved: {safe_name} → Rev {new_rev} for project #{project_id} - {doc_type}")
                
                # Log the action
                log_audit(user_id, "auto-upload dokumen (direct)", {
                    "project_id": int(project_id),
                    "project_name": project_name,
                    "item": item,
                    "part_no": part_no,
                    "doc_column": doc_type,
                    "file_name": safe_name,
                    "file_path": str(dest_path),
                    "revision": new_rev
                })
                
                # Auto-update status if all documents complete
                check_and_update_project_status(project_id, user_id)
        
        return True
    except Exception as e:
        import traceback
        error_msg = f"Error auto-uploading {uploaded_file.name}: {str(e)}\n{traceback.format_exc()}"
        st.error(error_msg)
        print(error_msg)  # Print to console for debugging
        return False

# --- Manajemen Dokumen (khusus Admin) ---
def manage_docs_page():
    st.subheader("Kelola Dokumen/Kolom Proyek")
    
    tab_auto, tab_add, tab_delete, tab_pref = st.tabs(["🤖 Auto Upload", "Tambah Dokumen", "Hapus Dokumen", "Preferensi Delegasi"])

    with tab_auto:
        st.markdown("#### 🤖 Auto-Detect & Upload Dokumen")
        st.info("📋 Upload dokumen dengan format nama: **[JENIS DOKUMEN] [PART NAME] [PART NUMBER] Rev.X**\n\n"
                "Contoh: `FMEA ENGINE BRACKET YHA (062A) BS-062A-2 Rev.0.pdf`\n\n"
                "Sistem akan otomatis mendeteksi jenis dokumen, part name, dan part number (jika ada), "
                "lalu mencocokkan dengan proyek yang ada (minimal 80% kecocokan).\n\n"
                "**✅ Format Nama File yang Didukung:**\n"
                "• Dengan part number: `FMEA CYLINDER LINER RDBSD-N REV.0`\n"
                "• Tanpa part number: `FMEA CASE DIFF REV.1` (matching hanya berdasarkan item name)\n"
                "• Part number di tengah: `FMEA DIFF CARRIER REAR Y4L REV.0`\n\n"
                "**🎯 Prioritas Upload (jika ada file duplikat untuk item yang sama):**\n"
                "1. **🔄 Nomor Revisi TERTINGGI** - REV.1 > REV.0, REV.01 > REV.0\n"
                "2. **📊 Kecocokan Nama Tertinggi** - Similarity % dengan item di sistem\n\n"
                "💡 *Format revisi yang didukung: REV.0, Rev.1, REV 01, Revision 2, R01*")
        
        st.warning("⚠️ **PENTING**: File yang diupload melalui Auto Upload akan masuk sebagai **PENDING** dan memerlukan "
                   "**approval dari Admin/Manager/SPV** sebelum benar-benar masuk ke sistem. "
                   "Cek halaman **📋 Approval List** untuk menyetujui atau menolak file.")
        
        uploaded_files = st.file_uploader(
            "Upload Dokumen (bisa multiple files)",
            type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls', 'doc', 'docx'],
            accept_multiple_files=True,
            key="auto_upload_docs"
        )
        
        if uploaded_files:
            if st.button("🚀 Proses Auto Upload", type="primary", use_container_width=True):
                results = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Group files by (doc_type, part_name, part_number) to handle duplicates
                file_groups = {}
                
                for uploaded_file in uploaded_files:
                    doc_info = extract_doc_info_from_filename(uploaded_file.name)
                    if doc_info:
                        key = (doc_info['doc_type'], doc_info['part_name'], doc_info['part_number'])
                        if key not in file_groups:
                            file_groups[key] = []
                        file_groups[key].append({
                            'file': uploaded_file,
                            'doc_info': doc_info
                        })
                    else:
                        # Handle files that can't be parsed
                        if None not in file_groups:
                            file_groups[None] = []
                        file_groups[None].append({
                            'file': uploaded_file,
                            'doc_info': None
                        })
                
                total_files = len(uploaded_files)
                processed = 0
                
                for group_key, group_files in file_groups.items():
                    # Handle unparseable files
                    if group_key is None:
                        for file_data in group_files:
                            results.append({
                                'file': file_data['file'].name,
                                'status': '❌ Gagal',
                                'reason': 'Tidak dapat mendeteksi jenis dokumen'
                            })
                            processed += 1
                            progress_bar.progress(processed / total_files)
                        continue
                    
                    # For each group, prioritize by date modified (newest first)
                    # Since Streamlit uploaded files don't have date metadata, we'll use filename similarity
                    # as primary sorting (already done in find_matching_project)
                    
                    doc_type, part_name, part_number = group_key
                    
                    # Find matching projects (get all matches for this group)
                    all_matches = find_matching_project(part_name, part_number, min_similarity=80, return_all_matches=True)
                    
                    if not all_matches:
                        # No match found for this group
                        for file_data in group_files:
                            results.append({
                                'file': file_data['file'].name,
                                'status': '⏭️ Skip',
                                'reason': f"Part Name/Number tidak ditemukan (detected: {part_name} / {part_number})"
                            })
                            processed += 1
                            progress_bar.progress(processed / total_files)
                        continue
                    
                    # Priority 1: Extract revision number from filename (REV.X, Rev.X, REV X, etc.)
                    # Priority 2: File similarity to item name
                    import re
                    
                    for file_data in group_files:
                        filename = file_data['file'].name
                        
                        # Look for revision patterns: REV.0, Rev.1, REV 01, Revision 2, etc.
                        # Patterns to match: REV.01, Rev.1, REV 0, Revision 2, R01, etc.
                        revision_patterns = [
                            r'(?:REV|Rev|rev|REVISION|Revision|revision|R)[\s._-]*(\d+(?:\.\d+)?)',
                        ]
                        
                        extracted_revision = 0.0  # Default revision 0
                        for pattern in revision_patterns:
                            matches = re.findall(pattern, filename)
                            if matches:
                                try:
                                    # Get the last match (in case there are multiple)
                                    rev_str = matches[-1]
                                    # Convert to float (handles both "0" and "0.1")
                                    extracted_revision = float(rev_str)
                                    break
                                except (ValueError, IndexError):
                                    continue
                        
                        file_data['extracted_revision'] = extracted_revision
                        
                        # Calculate file similarity
                        file_data['file_similarity'] = calculate_similarity(
                            filename,
                            all_matches[0]['item'] if all_matches else ""
                        )
                    
                    # Sort by: 1) Revision (highest first), 2) Similarity (highest first)
                    group_files.sort(key=lambda x: (
                        x['extracted_revision'],
                        x['file_similarity']
                    ), reverse=True)
                    
                    # Use the best match project (already sorted by similarity)
                    best_project_match = all_matches[0]
                    
                    # Process files in priority order (best filename match first)
                    for file_data in group_files:
                        uploaded_file = file_data['file']
                        doc_info = file_data['doc_info']
                        
                        status_text.text(f"Memproses: {uploaded_file.name}...")
                        
                        # Auto upload - no need to seek, we haven't read it yet
                        success = auto_upload_document(
                            uploaded_file,
                            doc_info['doc_type'],
                            best_project_match['project_id'],
                            st.session_state['user_id']
                        )
                        
                        if success:
                            # Show revision info if available
                            rev_info = ""
                            if file_data.get('extracted_revision') is not None and file_data['extracted_revision'] > 0:
                                rev_info = f" • 🔄 Rev: {file_data['extracted_revision']}"
                            
                            results.append({
                                'file': uploaded_file.name,
                                'status': '⏳ Pending Approval',
                                'reason': f"Upload ke: {best_project_match['item']} / {best_project_match['part_no']} - {doc_info['doc_type']} (Match: {best_project_match['similarity']:.1f}%{rev_info}) - Menunggu persetujuan"
                            })
                        else:
                            results.append({
                                'file': uploaded_file.name,
                                'status': '❌ Gagal',
                                'reason': 'Error saat upload - cek log error di atas'
                            })
                        
                        processed += 1
                        progress_bar.progress(processed / total_files)
                
                status_text.text("Selesai!")
                progress_bar.empty()
                
                # Show results
                st.markdown("---")
                st.markdown("### 📊 Hasil Auto Upload")
                
                results_df = pd.DataFrame(results)
                
                # Count successes
                pending_count = len([r for r in results if r['status'] == '⏳ Pending Approval'])
                skip_count = len([r for r in results if r['status'] == '⏭️ Skip'])
                fail_count = len([r for r in results if r['status'] == '❌ Gagal'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏳ Pending Approval", pending_count)
                with col2:
                    st.metric("⏭️ Skip", skip_count)
                with col3:
                    st.metric("❌ Gagal", fail_count)
                
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                
                if pending_count > 0:
                    st.success(f"📤 {pending_count} dokumen berhasil di-upload dan menunggu approval!")
                    st.info("💡 File akan masuk ke sistem setelah disetujui oleh **Admin/Manager/SPV** di halaman **📋 Approval List**.")
                    st.balloons()

    with tab_add:
        st.markdown("#### Tambah Dokumen Baru")
        new_doc_name = st.text_input("Nama Dokumen/Kolom Baru (contoh: 'Report Uji Coba')")
        
        # Opsi untuk menentukan apakah dokumen ini multiple file
        is_multiple = st.checkbox("Dukungan Unggahan Multiple Files")
        
        if st.button("Tambah Dokumen"):
            if new_doc_name:
                if add_dynamic_doc_column(new_doc_name, st.session_state['user_id']):
                    st.success(f"Dokumen '{new_doc_name}' berhasil ditambahkan! Silakan refresh halaman.")
                    st.rerun()
                else:
                    st.error("Gagal menambahkan dokumen.")
            else:
                st.warning("Nama dokumen tidak boleh kosong.")
    
    with tab_delete:
        st.markdown("#### Hapus Dokumen")
        current_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        if current_docs:
            doc_to_delete = st.selectbox("Pilih dokumen yang akan dihapus", current_docs)
            st.warning("Menghapus kolom akan menghapus data file yang terkait dengan kolom tersebut pada semua proyek! Aksi ini tidak dapat dibatalkan.")
            if st.button(f"Hapus Dokumen '{doc_to_delete}'"):
                if delete_doc_column(doc_to_delete, st.session_state['user_id']):
                    st.success(f"Dokumen '{doc_to_delete}' berhasil dihapus.")
                    st.rerun()
                else:
                    st.error("Gagal menghapus dokumen.")
        else:
            st.info("Tidak ada dokumen yang dapat dihapus.")

    with tab_pref:
        st.markdown("#### Preferensi Delegasi Otomatis")
        
        col_info2, col_refresh2 = st.columns([4, 1])
        with col_info2:
            st.info("💡 Set preferensi agar dokumen tertentu otomatis didelegasikan saat proyek baru dibuat (bisa lebih dari 1 user)")
        with col_refresh2:
            if st.button("🔄 Refresh Data", key="refresh_prefs_manage", help="Muat ulang daftar user terbaru"):
                st.session_state['pref_refresh_manage'] = True
                st.rerun()

        # Cache preferences dan users di session_state untuk menghindari query berulang
        # Auto-refresh jika cache tidak ada (user baru approved/registered)
        if ('cached_prefs_manage' not in st.session_state or 
            'cached_pids_manage' not in st.session_state or 
            st.session_state.get('pref_refresh_manage', False)):
            st.session_state['cached_prefs_manage'] = get_all_preferences()
            st.session_state['cached_pids_manage'] = get_all_pids()
            st.session_state['pref_refresh_manage'] = False
        
        prefs = st.session_state['cached_prefs_manage']
        pids = st.session_state['cached_pids_manage']
        
        if prefs:
            st.markdown("##### Preferensi Saat Ini")
            # Parse JSON untuk menampilkan multiple users
            prefs_display = []
            for p in prefs:
                try:
                    users_list = json.loads(p['delegated_to']) if p['delegated_to'] else []
                    if isinstance(users_list, str):
                        users_list = [users_list]
                    users_str = ", ".join(users_list) if users_list else "-"
                except (json.JSONDecodeError, TypeError):
                    users_str = p['delegated_to'] if p['delegated_to'] else "-"
                prefs_display.append({
                    'doc_name': p['doc_name'],
                    'delegated_to': users_str
                })
            st.dataframe(pd.DataFrame(prefs_display), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada preferensi delegasi yang disetel.")

        st.markdown("---")
        st.markdown("##### Tambah/Perbarui Preferensi")
        all_docs = DEFAULT_DOC_COLUMNS + get_dynamic_doc_columns()
        pref_doc = st.selectbox("Dokumen", all_docs, key="pref_doc_select_manage")
        
        # Get existing preference untuk dokumen ini
        existing_pref = next((p for p in prefs if p['doc_name'] == pref_doc), None)
        existing_users = []
        if existing_pref:
            try:
                existing_users = json.loads(existing_pref['delegated_to']) if existing_pref['delegated_to'] else []
                if isinstance(existing_users, str):
                    existing_users = [existing_users]
            except (json.JSONDecodeError, TypeError):
                existing_users = [existing_pref['delegated_to']] if existing_pref['delegated_to'] else []
        
        pref_users = st.multiselect(
            "Delegasikan ke (bisa pilih lebih dari 1)",
            pids,
            default=[u for u in existing_users if u in pids],
            key="pref_user_select_manage"
        )
        
        if st.button("💾 Simpan Preferensi", key="save_pref_manage"):
            if pref_users:
                # Simpan sebagai JSON string
                users_json = json.dumps(pref_users)
                upsert_preference(pref_doc, users_json, st.session_state['user_id'])
                st.success(f"✅ Preferensi tersimpan: **{pref_doc}** → {', '.join(pref_users)}")
                # Refresh cache agar data terbaru muncul
                st.session_state['pref_refresh_manage'] = True
                st.rerun()
            else:
                st.error("❌ Pilih minimal 1 user untuk delegasi!")

        st.markdown("---")
        st.markdown("##### 🔄 Terapkan Preferensi ke Semua Proyek")
        st.warning("⚠️ **Perhatian!** Fitur ini akan **mengganti delegasi** di SEMUA proyek dengan preferensi yang telah Anda set di atas.")
        
        col_apply1, col_apply2 = st.columns([3, 1])
        with col_apply1:
            st.info(f"📊 Jumlah preferensi yang akan diterapkan: **{len(prefs)}** dokumen")
        with col_apply2:
            if st.button("🚀 Apply ke Semua Proyek", type="primary", use_container_width=True, key="apply_all_manage"):
                with st.spinner("Sedang menerapkan preferensi ke semua proyek..."):
                    project_count, message = apply_preferences_to_all_projects(st.session_state['user_id'])
                    
                    if project_count > 0:
                        st.success(f"✅ {message}")
                        st.balloons()
                        
                        # Show details
                        with st.expander("📋 Detail Update"):
                            for p in prefs:
                                try:
                                    users_list = json.loads(p['delegated_to']) if p['delegated_to'] else []
                                    if isinstance(users_list, str):
                                        users_list = [users_list]
                                    users_str = ", ".join(users_list) if users_list else "-"
                                except (json.JSONDecodeError, TypeError):
                                    users_str = p['delegated_to'] if p['delegated_to'] else "-"
                                st.write(f"✓ **{p['doc_name']}** → {users_str}")
                        
                        st.info("💡 Silakan cek menu **Dashboard** atau **Manajemen Proyek** untuk melihat perubahan.")
                    else:
                        st.error(f"❌ {message}")
        
        st.markdown("---")
        st.markdown("##### Hapus Preferensi")
        if prefs:
            doc_to_remove = st.selectbox("Pilih dokumen untuk dihapus preferensinya", [p['doc_name'] for p in prefs], key="pref_doc_remove_manage")
            if st.button("🗑️ Hapus Preferensi", key="delete_pref_manage"):
                delete_preference(doc_to_remove, st.session_state['user_id'])
                st.success("✅ Preferensi dihapus.")
                # Refresh cache agar data terbaru muncul
                st.session_state['pref_refresh_manage'] = True
                st.rerun()
        else:
            st.info("Tidak ada preferensi untuk dihapus.")

# --- Audit Log Page (khusus Admin & Manager & SPV) ---
def show_audit_log_page():
    st.header("Audit Log")
    st.info("Mencatat semua aktivitas penting pengguna, termasuk login, manajemen proyek, dan perubahan pada dokumen.")
    
    conn = get_conn()
    logs_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
    users_df = pd.read_sql_query("SELECT id, full_name FROM users", conn)
    conn.close()
    
    # Gabungkan logs_df dengan users_df untuk mendapatkan full_name
    logs_df = pd.merge(logs_df, users_df, left_on='user_id', right_on='id', how='left')
    
    if logs_df.empty:
        st.info("Belum ada aktivitas yang tercatat.")
        return
    
    projects = set()
    for _, row in logs_df.iterrows():
        try:
            details = json.loads(row['details'])
            if 'project_name' in details:
                projects.add(details['project_name'])
        except (json.JSONDecodeError, TypeError):
            continue
    
    users = sorted(logs_df['user_id'].unique().tolist())
    # Perbaikan: Hapus nilai NaN sebelum disortir
    full_names_raw = logs_df['full_name'].unique().tolist()
    full_names = sorted([name for name in full_names_raw if pd.notna(name)])
    actions = sorted(logs_df['action'].unique().tolist())
    projects = sorted(list(projects))

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        # Tambahkan filter full_name
        selected_full_name = st.selectbox("Filter by Nama Lengkap", ['All'] + full_names)
        selected_action = st.selectbox("Filter by Action", ['All'] + actions)
    with col2:
        selected_project = st.selectbox("Filter by Project", ['All'] + projects)
        start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
        end_date = st.date_input("End Date", value=datetime.date.today())

    filtered_df = logs_df.copy()
    filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])

    # Filter by date range
    filtered_df = filtered_df[
        (filtered_df['timestamp'].dt.date >= start_date) &
        (filtered_df['timestamp'].dt.date <= end_date)
    ]

    # Filter by user and action
    if selected_full_name != 'All':
        filtered_df = filtered_df[filtered_df['full_name'] == selected_full_name]
    if selected_action != 'All':
        filtered_df = filtered_df[filtered_df['action'] == selected_action]

    # Filter by project name
    if selected_project != 'All':
        def filter_by_project(details_str):
            try:
                details = json.loads(details_str)
                return details.get('project_name') == selected_project
            except (json.JSONDecodeError, TypeError):
                return False
        filtered_df = filtered_df[filtered_df['details'].apply(filter_by_project)]

    if filtered_df.empty:
        st.warning("Tidak ada data yang cocok dengan kriteria filter.")
    else:
        # Format the log output for better readability
        log_rows = []
        for _, row in filtered_df.iterrows():
            timestamp = pd.to_datetime(row['timestamp']).strftime('%d-%m-%Y %H:%M:%S')
            full_name = row['full_name']
            action = row['action']
            
            try:
                details = json.loads(row['details'])
            except (json.JSONDecodeError, TypeError):
                details = {}
            
            detail_str = "N/A"
            if action == "menambah proyek":
                detail_str = f"Proyek: **{details.get('project_name')}**, Item: **{details.get('item')}**"
            elif action == "menghapus proyek":
                detail_str = f"Proyek: **{details.get('project_name')}**"
            elif action == "mengedit proyek":
                detail_str = f"Proyek: **{details.get('project_name')}**"
            elif action == "mendelegasikan dokumen":
                detail_str = (
                    f"Dokumen: **{details.get('doc_column')}**, "
                    f"Didelegasikan ke: **{details.get('delegated_to')}**"
                )
                if 'start_date' in details and 'end_date' in details:
                    detail_str += f", Tanggal: {details.get('start_date')} s/d {details.get('end_date')}"
            elif action == "menyetujui dokumen":
                detail_str = f"Dokumen: **{details.get('doc_column')}**"
            elif action == "menolak dokumen":
                detail_str = f"Dokumen: **{details.get('doc_column')}**"
            elif action == "mengunggah file pending":
                detail_str = f"Mengunggah file pending untuk dokumen: **{details.get('doc_column')}**"
            elif action == "membatalkan pengajuan dokumen":
                detail_str = f"Dokumen: **{details.get('doc_column')}**"
            elif action == "mengupdate status proyek ke Done":
                detail_str = f"Proyek: **{details.get('project_name')}** - Semua dokumen lengkap"
            elif action == "login berhasil":
                detail_str = "Login berhasil"
            elif action == "login gagal":
                detail_str = "Login gagal"
            elif action == "mengubah role pengguna":
                detail_str = f"User: **{details.get('user_id')}**, Role Baru: **{details.get('new_role')}**"
            
            log_rows.append({
                'Tanggal & Waktu': timestamp,
                'Nama': full_name if pd.notna(full_name) else row['user_id'],
                'Aksi': action,
                'Detail': detail_str
            })

        log_df = pd.DataFrame(log_rows)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

# --- Tambahkan Kode Footer di Sini ---
# ...existing code...
st.markdown("""
    <style>
        .footer {
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            background-color: #f0f2f6;
            color: #333;
            text-align: center;
            padding: 5px;
            font-size: 14px;
            border-top: 1px solid #ddd;
            z-index: 9999;
        }
        .footer p {
            margin-bottom: 2px;
            line-height: 1.2;
        }
        .footer a {
            color: #4b89ff;
            text-decoration: none;
            font-weight: bold;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        /* Tambahkan padding bawah pada konten utama agar tidak tertutup footer */
        .main .block-container {
            padding-bottom: 48px;
        }
    </style>
    <div class="footer">
        <p>Developed by <b>Galih Primananda</b> </p>
        <p>
            <a href="https://instagram.com/glh_prima/" target="_blank">Instagram</a> |
            <a href="https://linkedin.com/in/galihprime/" target="_blank">LinkedIn</a> |
            <a href="https://github.com/PrimeFox59" target="_blank">GitHub</a> |
            <a href="https://drive.google.com/drive/folders/11ov7TpvOZ3m7k5GLRAbE2WZFbGVK2t7i?usp=sharing" target="_blank">Portfolio</a> |
            <a href="https://fastwork.id/user/glh_prima" target="_blank">Fastwork for Services & Collaboration</a>
        </p>
    </div>
""", unsafe_allow_html=True)
# ...existing code...


# --- Jalankan Aplikasi ---
init_db()

# Inisialisasi session_state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Solusi: Inisialisasi 'page' key jika belum ada
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'

if 'db_initialized' not in st.session_state:
    st.session_state['db_initialized'] = True

if st.session_state['logged_in']:
    show_main_page()
else:
    if st.session_state['page'] == 'register':
        show_register_page()
    else:
        show_login_page()