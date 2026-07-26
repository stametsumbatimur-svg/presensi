import streamlit as st
import pandas as pd
import sqlite3
import math
import os
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# KONFIGURASI LOKASI KANTOR 
# ==========================================
OFFICE_LAT = -6.1753924
OFFICE_LNG = 106.8271528
MAX_RADIUS_METERS = 50.0  # Radius maksimal dalam meter

# Buat folder penyimpanan foto jika belum ada
FOLDER_FOTO = "foto_absensi"
os.makedirs(FOLDER_FOTO, exist_ok=True)

# ==========================================
# DATABASE SQLITE
# ==========================================
def init_db():
    with sqlite3.connect('absensi.db') as conn:
        c = conn.cursor()
        # Tabel Pegawai
        c.execute('''CREATE TABLE IF NOT EXISTS pegawai (
                        nip TEXT PRIMARY KEY,
                        nama TEXT
                    )''')
        # Tabel Presensi (Hanya menyimpan data yang diperlukan)
        c.execute('''CREATE TABLE IF NOT EXISTS presensi (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nip TEXT,
                        nama TEXT,
                        shift TEXT,
                        jenis_absen TEXT,
                        waktu TEXT,
                        status_waktu TEXT,
                        foto_path TEXT
                    )''')
        
        # Insert Data Pegawai Bawaan
        c.execute("SELECT COUNT(*) FROM pegawai")
        if c.fetchone()[0] == 0:
            dummy_data = [('1001', 'Ahmad Budi'), 
                          ('1002', 'Siti Rahmawati'), 
                          ('1003', 'John Doe')]
            c.executemany("INSERT INTO pegawai VALUES (?, ?)", dummy_data)
        conn.commit()

init_db()

# ==========================================
# FUNGSI VALiDASI LOGIKA & JARAK
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def hitung_status_waktu(shift, jenis_absen, dt_now):
    """
    Hitung status Tepat Waktu / Terlambat
    - Pagi  : Shift 06.00 - 18.00 (Toleransi Masuk s/d 06.15)
    - Malam : Shift 18.00 - 06.00 (Toleransi Masuk s/d 18.15)
    """
    jam_menit = dt_now.time()
    
    if jenis_absen == "Masuk":
        if shift == "Pagi":
            # Batas toleransi tepat waktu untuk Pagi (06.15)
            batas_pagi = datetime.strptime("06:15:00", "%H:%M:%S").time()
            if jam_menit > batas_pagi and jam_menit < datetime.strptime("18:00:00", "%H:%M:%S").time():
                return "Terlambat"
            return "Tepat Waktu"
            
        elif shift == "Malam":
            # Batas toleransi tepat waktu untuk Malam (18.15)
            batas_malam = datetime.strptime("18:15:00", "%H:%M:%S").time()
            # Terlambat jika lewat 18.15 malam atau sebelum jam 06.00 pagi
            if jam_menit > batas_malam or jam_menit < datetime.strptime("06:00:00", "%H:%M:%S").time():
                return "Terlambat"
            return "Tepat Waktu"
            
    elif jenis_absen == "Pulang":
        if shift == "Pagi":
            if jam_menit < datetime.strptime("18:00:00", "%H:%M:%S").time():
                return "Pulang Cepat"
            return "Sesuai Jadwal"
        elif shift == "Malam":
            if jam_menit < datetime.strptime("06:00:00", "%H:%M:%S").time() and jam_menit >= datetime.strptime("18:00:00", "%H:%M:%S").time():
                return "Pulang Cepat"
            return "Sesuai Jadwal"
            
    return "Tepat Waktu"

# ==========================================
# TAMPILAN UNTUK PENGGUNA (UI)
# ==========================================
st.set_page_config(page_title="Sistem Presensi Pegawai", page_icon="📍", layout="centered")
st.title("📍 Aplikasi Presensi Online")

# 1. Input NIP Pegawai
st.subheader("1. Identitas Pegawai")
nip_input = st.text_input("Masukkan Nomor Pegawai (NIP):", placeholder="Contoh: 1001")

nama_pegawai = None
if nip_input:
    with sqlite3.connect('absensi.db') as conn:
        c = conn.cursor()
        c.execute("SELECT nama FROM pegawai WHERE nip = ?", (nip_input,))
        res = c.fetchone()
        if res:
            nama_pegawai = res[0]
            st.success(f"👤 Nama Pegawai: **{nama_pegawai}**")
        else:
            st.error("❌ NIP tidak terdaftar.")

# 2. Detail Jam Shift & Waktu
col1, col2 = st.columns(2)
with col1:
    jenis_absen = st.selectbox("Jenis Presensi:", ["Masuk", "Pulang"])
with col2:
    shift = st.selectbox("Shift Dinas:", ["Pagi", "Malam"])

st.caption("ℹ️ *Shift Pagi (06.00 - 18.00) | Shift Malam (18.00 - 06.00)*")
st.markdown("---")

# 3. Validasi Lokasi (Diukur tapi tidak disimpan ke DB)
st.subheader("2. Verifikasi Lokasi Kantor")
lokasi = streamlit_geolocation()

user_lat, user_lng = None, None
posisi_valid = False

if lokasi and lokasi.get('latitude') and lokasi.get('longitude'):
    user_lat = lokasi['latitude']
    user_lng = lokasi['longitude']
    jarak = calculate_distance(OFFICE_LAT, OFFICE_LNG, user_lat, user_lng)
    
    if jarak <= MAX_RADIUS_METERS:
        st.success(f"✅ Anda berada di area kantor (Jarak: {jarak:.1f} meter)")
        posisi_valid = True
    else:
        st.error(f"❌ Di luar area kantor (Jarak: {jarak:.1f} meter, Maks: {MAX_RADIUS_METERS}m)")

st.markdown("---")

# 4. Ambil Foto Bukti
st.subheader("3. Foto Bukti Kehadiran")
metode_foto = st.radio("Pilih Kamera:", ["Kamera HP / File Upload", "Kamera Langsung Web"], horizontal=True)

foto_selfie = None
if metode_foto == "Kamera HP / File Upload":
    foto_selfie = st.file_uploader("Ambil Foto dari Kamera HP", type=["jpg", "jpeg", "png"])
else:
    foto_selfie = st.camera_input("Ambil Foto Kamera")

st.markdown("---")

# 5. Tombol Simpan
if st.button("💾 Simpan Presensi", type="primary", use_container_width=True):
    if not nip_input or not nama_pegawai:
        st.error("Masukkan NIP pegawai yang valid.")
    elif not posisi_valid:
        st.error("Gagal: Anda harus berada di area kantor untuk melakukan presensi.")
    elif foto_selfie is None:
        st.error("Gagal: Wajib mengambil/mengunggah foto bukti kehadiran.")
    else:
        waktu_sekarang = datetime.now()
        str_waktu = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
        
        # Hitung Otomatis Terlambat / Tepat Waktu
        status_waktu = hitung_status_waktu(shift, jenis_absen, waktu_sekarang)
        
        # Simpan file foto ke folder foto_absensi
        ext = foto_selfie.name.split('.')[-1] if hasattr(foto_selfie, 'name') else 'jpg'
        nama_file_foto = f"{FOLDER_FOTO}/{nip_input}_{jenis_absen}_{waktu_sekarang.strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        with open(nama_file_foto, "wb") as f:
            f.write(foto_selfie.getbuffer())
        
        # Simpan data presensi ke Database
        with sqlite3.connect('absensi.db') as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO presensi 
                         (nip, nama, shift, jenis_absen, waktu, status_waktu, foto_path) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                      (nip_input, nama_pegawai, shift, jenis_absen, str_waktu, status_waktu, nama_file_foto))
            conn.commit()
            
        if status_waktu == "Terlambat":
            st.warning(f"⚠️ Presensi Berhasil Disimpan pada {str_waktu}. Status: **TERLAMBAT**.")
        else:
            st.success(f"🎉 Presensi Berhasil Disimpan pada {str_waktu}. Status: **{status_waktu.upper()}**.")

# ==========================================
# ADMIN REKAP ABSENSI (TERPISAH TIAP NIP)
# ==========================================
st.markdown("---")
with st.expander("📊 Rekap Absensi & Laporan (Khusus Admin)"):
    with sqlite3.connect('absensi.db') as conn:
        df = pd.read_sql_query("SELECT nip, nama, shift, jenis_absen, waktu, status_waktu, foto_path FROM presensi ORDER BY id DESC", conn)
        
        if not df.empty:
            # Fitur Memisah Data Per NIP
            list_nip = ["Semua NIP"] + list(df['nip'].unique())
            pilihan_nip = st.selectbox("Filter Tampilan Berdasarkan NIP:", list_nip)
            
            if pilihan_nip != "Semua NIP":
                df_filtered = df[df['nip'] == pilihan_nip]
            else:
                df_filtered = df
                
            st.dataframe(df_filtered, use_container_width=True)
            
            # Download Rekap CSV
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download Rekap CSV ({pilihan_nip})",
                data=csv,
                file_name=f"rekap_absensi_{pilihan_nip}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.info("Belum ada data presensi yang tersimpan.")
