# Project Monitor IATF

Sistem Monitoring & Kontrol Dokumen IATF 16949 berbasis Web Application.

---

## 🏗️ Arsitektur & Spesifikasi

- **Backend:** Python 3.13 (Flask, SQLAlchemy, Pandas, OpenPyXL, Flask-CORS)
- **Frontend:** React + Vite Single Page Application (Tailwind CSS, Lucide Icons)
- **Database:** SQLite (`projects.db`)
- **Storage:** Folder `uploads/` (Dokumen PDF, Drawing, Excel, Word, Image)
- **Port:** `5002`
- **Process Manager:** PM2 (`project-monitor-iatf`)
- **Public Gateway:** Cloudflare Tunnel Ingress (`https://iatf.primeprojectx.net`)

---

## 📂 Struktur Direktori

```text
D:\0 Running apps\IATF\
├── projects.db                  # Database Utama SQLite (Production)
├── uploads/                     # Direktori Penyimpanan Dokumen Fisik
└── ProjectMonitorIATF-source/   # Repositori Source Code
    ├── app.py                   # Entry point aplikasi Flask (Port 5002)
    ├── config.py                # Konfigurasi database, path uploads, secret key
    ├── models.py                # Definisi ORM SQLAlchemy (User, Project, Document, Revision, AuditLog)
    ├── requirements.txt         # Daftar dependency Python
    ├── dist/                    # Bundle frontend produksi (HTML, CSS, JS)
    │   ├── index.html
    │   └── assets/
    └── routes/                  # Modular Blueprint Endpoints
        ├── __init__.py
        ├── users.py             # Login, Registrasi, User Management, Approval
        ├── projects.py          # CRUD Proyek, Metadata Filter, Statistik, Import Excel
        ├── documents.py         # Upload/View/Download Dokumen, Smart Bulk Matching, Revisi
        ├── document_types.py    # Master Jenis Dokumen IATF
        └── audit.py             # Activity & Audit Logging
```

---

## 🚀 Manajemen Operasional (PM2)

- **Cek Status Service:**
  ```bash
  pm2 list
  ```
- **Restart Service:**
  ```bash
  pm2 restart project-monitor-iatf
  ```
- **Lihat Log Live:**
  ```bash
  pm2 logs project-monitor-iatf --lines 50
  ```
- **Menjalankan Manual (Standalone Dev):**
  ```bash
  cd "D:\0 Running apps\IATF\ProjectMonitorIATF-source"
  python app.py
  ```
