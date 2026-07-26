import streamlit as st
import pandas as pd
import sqlite3
import math
from datetime import datetime
# Modul pihak ketiga untuk mengambil GPS di Streamlit
# Harus diinstall terlebih dahulu: pip install streamlit-geolocation
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# KONFIGURASI LOKASI KANTOR 
# ==========================================
# Ganti dengan koordinat asli kantor Anda (Contoh di bawah adalah Monas, Jakarta)
OFFICE_LAT = -9.66927743077488 
OFFICE_LNG = 120.30029710982076
MAX_RADIUS_METERS = 10.0  # Batas radius 50 meter

# ==========================================
# INISIALISASI DATABASE SQLITE
# ==========================================
def init_db():
    with sqlite3.connect('absensi.db') as conn:
        c = conn.cursor()
        # Tabel Pegawai (Database Karyawan)
        c.execute('''CREATE TABLE IF NOT EXISTS pegawai (
                        nip TEXT PRIMARY KEY,
                        nama TEXT
                    )''')
        # Tabel Presensi (Log Masuk/Pulang)
        c.execute('''CREATE TABLE IF NOT EXISTS presensi (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nip TEXT,
                        nama TEXT,
                        waktu TEXT,
                        jenis_absen TEXT,
                        shift TEXT,
                        latitude REAL,
                        longitude REAL,
                        jarak REAL,
                        status TEXT,
                        foto_tersimpan BOOLEAN
                    )''')
        
        # Insert Data Pegawai Dummy Jika Tabel Masih Kosong
        c.execute("SELECT COUNT(*) FROM pegawai")
        if c.fetchone()[0] == 0:
            dummy_data = [('1001', 'Ahmad Budi'), 
                          ('1002', 'Siti Rahmawati'), 
                          ('1003', 'John Doe')]
            c.executemany("INSERT INTO pegawai VALUES (?, ?)", dummy_data)
        conn.commit()

init_db()

# ==========================================
# FUNGSI HAVERSINE (HITUNG JARAK)
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius bumi dalam meter
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================
# ANTARMUKA STREAMLIT (UI)
# ==========================================
st.set_page_config(page_title="Sistem Presensi Karyawan", page_icon="📍", layout="centered")

st.title("📍 Aplikasi Presensi & Geofencing")
st.markdown("**Silakan masukkan NIP, dapatkan koordinat lokasi, dan ambil foto selfie.**")

# 1. Input Nomor Induk Pegawai (Tanpa Login)
st.subheader("1. Identitas Pegawai")
nip_input = st.text_input("Masukkan Nomor Pegawai (NIP):", placeholder="Contoh: 1001 atau 1002")

nama_pegawai = None
if nip_input:
    with sqlite3.connect('absensi.db') as conn:
        c = conn.cursor()
        c.execute("SELECT nama FROM pegawai WHERE nip = ?", (nip_input,))
        result = c.fetchone()
        if result:
            nama_pegawai = result[0]
            st.success(f"👤 Pegawai Ditemukan: **{nama_pegawai}**")
        else:
            st.error("❌ NIP tidak ditemukan di database. Pastikan NIP benar.")

# 2. Detail Kehadiran (Dinas & Jenis Absen)
col1, col2 = st.columns(2)
with col1:
    jenis_absen = st.selectbox("Jenis Presensi:", ["Masuk", "Pulang"])
with col2:
    shift = st.selectbox("Keterangan Dinas (Shift):", ["Pagi", "Malam"])

st.markdown("---")

# 3. Validasi Lokasi (Geolocation API)
st.subheader("2. Verifikasi Lokasi Geofencing")
st.info("Klik tombol di bawah ini untuk mengambil titik koordinat GPS Anda.")
lokasi = streamlit_geolocation()

user_lat, user_lng = None, None
if lokasi and lokasi.get('latitude') and lokasi.get('longitude'):
    user_lat = lokasi['latitude']
    user_lng = lokasi['longitude']
    jarak = calculate_distance(OFFICE_LAT, OFFICE_LNG, user_lat, user_lng)
    
    st.write(f"🗺️ **Koordinat Anda:** `{user_lat}, {user_lng}`")
    st.write(f"📏 **Jarak ke Kantor:** `{jarak:.2f} meter`")
    
    if jarak <= MAX_RADIUS_METERS:
        st.success("✅ Lokasi Valid. Anda berada di dalam area kantor.")
    else:
        st.error(f"❌ Lokasi Ditolak. Anda berada di luar radius izin (Maks {MAX_RADIUS_METERS}m).")

st.markdown("---")

# 4. Anti-Fake GPS (Liveness Check via Selfie)
st.subheader("3. Bukti Kehadiran (Anti-Fake GPS)")
st.warning("Untuk mencegah manipulasi GPS (Fake Location), **wajib** menyertakan foto Selfie di lokasi kerja saat ini.")
foto_selfie = st.camera_input("Ambil Foto Kamera")

st.markdown("---")

# 5. Eksekusi Simpan ke Database
if st.button("💾 Simpan Presensi", type="primary", use_container_width=True):
    if not nip_input or not nama_pegawai:
        st.error("Gagal: Mohon masukkan NIP yang valid.")
    elif user_lat is None or user_lng is None:
        st.error("Gagal: Mohon ambil titik koordinat lokasi terlebih dahulu.")
    elif foto_selfie is None:
        st.error("Gagal: Foto Selfie wajib diambil untuk validasi Anti-Fake GPS.")
    else:
        # Hitung final
        jarak_final = calculate_distance(OFFICE_LAT, OFFICE_LNG, user_lat, user_lng)
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_absen = "Diterima" if jarak_final <= MAX_RADIUS_METERS else "Ditolak (Luar Area)"
        
        # Simpan ke DB
        with sqlite3.connect('absensi.db') as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO presensi 
                         (nip, nama, waktu, jenis_absen, shift, latitude, longitude, jarak, status, foto_tersimpan) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (nip_input, nama_pegawai, waktu_sekarang, jenis_absen, shift, 
                       user_lat, user_lng, jarak_final, status_absen, True))
            conn.commit()
        
        if jarak_final <= MAX_RADIUS_METERS:
            st.success(f"🎉 Presensi {jenis_absen} berhasil! Tercatat pada {waktu_sekarang}.")
            st.balloons()
        else:
            st.error(f"⚠️ Data log tersimpan, namun presensi DITOLAK karena Anda berjarak {jarak_final:.1f} meter (Di luar radius).")

# ==========================================
# DASHBOARD ADMIN TAMPILAN DATA (Opsional)
# ==========================================
st.markdown("---")
with st.expander("📊 Lihat Database Presensi (Khusus Admin)"):
    with sqlite3.connect('absensi.db') as conn:
        df = pd.read_sql_query("SELECT id, nip, nama, waktu, jenis_absen, shift, jarak, status FROM presensi ORDER BY id DESC", conn)
        st.dataframe(df, use_container_width=True)