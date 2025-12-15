# 📊 Project Monitoring IATF

Sistem monitoring project berbasis web untuk mendukung pelaporan, visualisasi, dan pengelolaan progres project IATF secara efisien dan transparan.

---

## 🚀 Deskripsi

**Project Monitoring IATF** adalah aplikasi berbasis Streamlit yang dirancang untuk membantu tim dalam memantau, mencatat, dan menganalisis perkembangan project IATF (International Automotive Task Force) secara real-time. Dengan antarmuka yang user-friendly, aplikasi ini memudahkan pelaporan, visualisasi data, dan kolaborasi antar anggota tim.

---

## ✨ Fitur Utama

- **Form Input Progres**: Input data progres project secara periodik
- **Dashboard Visualisasi**: Grafik dan tabel interaktif untuk analisis progres
- **Export Data**: Download laporan dalam format Excel
- **Filter & Search**: Cari dan filter data berdasarkan kriteria tertentu
- **Multi-user Support**: Bisa digunakan oleh banyak user secara bersamaan
- **Notifikasi Otomatis**: (Opsional, jika diaktifkan) Pengingat update progres

---

## 🗂️ Struktur Project

```
Project Monitoring IATF/
│
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
├── LICENSE                 # MIT License
├── start server.bat        # Windows batch file to start app
├── start.vbs               # Windows script to start app
├── note.txt                # Catatan atau dokumentasi tambahan
├── excel_kaizen/           # (Jika ada) Folder laporan Excel
├── uploads/                # (Jika ada) Folder upload file
```

---

## 🛠️ Instalasi

### Prasyarat
- Python 3.8 atau lebih tinggi
- pip (Python package manager)

### Langkah Instalasi

1. **Clone repository**
   ```bash
   git clone <repo-url>
   cd "Project Monitoring IATF"
   ```
2. **(Opsional) Buat virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   # atau
   source venv/bin/activate  # Linux/Mac
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Jalankan aplikasi**
   ```bash
   streamlit run app.py
   ```
5. **Akses aplikasi**
   Buka browser ke: `http://localhost:8501`

---

## 📖 Cara Penggunaan

1. **Input Data**: Masukkan progres project melalui form yang tersedia
2. **Lihat Dashboard**: Pantau progres melalui grafik dan tabel
3. **Filter Data**: Gunakan fitur filter/search untuk analisis spesifik
4. **Export**: Download data ke Excel untuk pelaporan

---

## 🎨 Teknologi yang Digunakan
- **Streamlit**: Web app framework
- **Pandas**: Data processing
- **Openpyxl**: Excel export
- **Altair**: Visualisasi data (jika digunakan)
- **Pillow**: Image processing (jika ada upload gambar)

---

## 📝 Lisensi

Aplikasi ini menggunakan lisensi MIT. Silakan lihat file [LICENSE](LICENSE) untuk detail.

---

## 🤝 Kontribusi

Kontribusi sangat terbuka! Silakan fork, buat branch, dan ajukan pull request untuk fitur/bugfix baru.

---

## 📞 Kontak

Developer: Galih Primananda  
[Instagram](https://instagram.com/glh_prima/) | [LinkedIn](https://linkedin.com/in/galihprime/) | [GitHub](https://github.com/PrimeFox59)

---

**Selamat menggunakan Project Monitoring IATF!**
