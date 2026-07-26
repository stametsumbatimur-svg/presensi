# Panduan Lengkap Aplikasi Presensi Streamlit (Geofencing & Anti-Fake GPS)

Aplikasi presensi web berbasis Python/Streamlit ini telah disesuaikan dengan permintaan:
1. **Tanpa Login:** Absen hanya dengan memasukkan Nomor Induk Pegawai (NIP).
2. **Database:** Menggunakan SQLite terintegrasi yang menyimpan data pegawai, jam masuk/pulang, dan keterangan dinas (Pagi/Malam).
3. **Anti-Fake Location:** Menggunakan gabungan validasi titik koordinat GPS + Liveness Check (Fitur Kamera Wajib) untuk memastikan kehadiran fisik, menangkal aplikasi VPN/Fake GPS murni.

---

## 🚀 Cara Instalasi & Menjalankan

### 1. Persiapan Environment
Pastikan Python sudah terinstal di komputer. Buka Terminal / Command Prompt (CMD), lalu arahkan ke folder ini dan instal seluruh library yang dibutuhkan:
```bash
pip install -r requirements.txt
```

### 2. Mengubah Konfigurasi Lokasi Kantor Anda
Sebelum menjalankan aplikasi, Anda WAJIB mengubah titik koordinat (Latitude & Longitude) kantor Anda.
Buka file `app_presensi.py` menggunakan Notepad atau Text Editor, lalu cari baris ini di bagian atas:
```python
OFFICE_LAT = -9.66927743077488 
OFFICE_LNG = 120.30029710982076
MAX_RADIUS_METERS = 10.0
```

### 3. Jalankan Aplikasi
Di terminal yang sama, ketikkan perintah berikut:
```bash
streamlit run app_presensi.py
```
Aplikasi akan secara otomatis terbuka pada Browser di alamat `http://localhost:8501`.

---

## 👥 Akun Dummy Bawaan Sistem
Sistem ini menggunakan SQLite ringan yang akan dibuat otomatis (`absensi.db`). 
Secara default, ada 3 NIP percobaan yang sudah terdaftar otomatis di tabel pegawai:
* **1001** (Ahmad Budi)
* **1002** (Siti Rahmawati)
* **1003** (John Doe)

*(Untuk menambah/mengubah pegawai, Anda dapat menggunakan aplikasi 'DB Browser for SQLite' dan membuka file `absensi.db` yang ter-generate).*