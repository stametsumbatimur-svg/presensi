import streamlit as st
import pandas as pd
import sqlite3
import math
import os
import io
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

# Library Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# KONFIGURASI LOKASI KANTOR 
# ==========================================
OFFICE_LAT = -9.66927743077488 
OFFICE_LNG = 120.30029710982076
MAX_RADIUS_METERS = 100.0  # Radius 100 meter

# ==========================================
# FUNGSI UPLOAD KE GOOGLE DRIVE
# ==========================================
def upload_to_gdrive(file_buffer, file_name):
    """Mengunggah foto langsung dari memori ke Google Drive"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds_dict = dict(st.secrets["gcp_service_account"])
        folder_id = st.secrets["FOLDER_ID"]

        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }

        media = MediaIoBaseUpload(io.BytesIO(file_buffer), mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

        return file.get('webViewLink')  # Mengembalikan link foto di Google Drive
    except Exception as e:
        st.error(f"Gagal mengunggah foto ke Google Drive: {e}")
        return None

# ==========================================
# DATABASE SQLITE & AUTO-MIGRATION
# ==========================================
def init_db():
    with sqlite3.connect('absensi.db') as conn:
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS pegawai (
                        nip TEXT PRIMARY KEY,
                        nama TEXT
                    )''')
                    
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
        
        # Migrasi kolom foto_path jika belum ada
        c.execute("PRAGMA table_info(presensi)")
        existing_columns = [column[1] for column in c.fetchall()]
        if 'status_waktu' not in existing_columns:
            c.execute("ALTER TABLE presensi ADD COLUMN status_waktu TEXT")
        if 'foto_path' not in existing_columns:
            c.execute("ALTER TABLE presensi ADD COLUMN foto_path TEXT")

        # Insert pegawai bawaan jika kosong
        c.execute("SELECT COUNT(*) FROM pegawai")
        if c.fetchone()[0] == 0:
            dummy_data = [('1001', 'Ahmad Budi'), 
                          ('1002', 'Siti Rahmawati'), 
                          ('1003', 'John Doe')]
            c.executemany("INSERT INTO pegawai VALUES (?, ?)", dummy_data)
        conn.commit()

init_db()

# ==========================================
# FUNGSI HAVERSINE & LOGIKA WAKTU
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def hitung_status_waktu(shift, jenis_absen, dt_now):
    jam_menit = dt_now.time()
    
    if jenis_absen == "Masuk":
        if shift == "Pagi":
            batas_pagi = datetime.strptime("06:15:00", "%H:%M:%S").time()
            if jam_menit > batas_pagi and jam_menit < datetime.strptime("18:00:00", "%H:%M:%S").time():
                return "Terlambat"
            return "Tepat Waktu"
            
        elif shift == "Malam":
            batas_malam = datetime.strptime("18:15:00", "%H:%M:%S").time()
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
            st.error("❌ NIP tidak terdaftar di database.")

# 2. Detail Shift & Jenis Absen
col1, col2 = st.columns(2)
with col1:
    jenis_absen = st.selectbox("Jenis Presensi:", ["Masuk", "Pulang"])
with col2:
    shift = st.selectbox("Shift Dinas:", ["Pagi", "Malam"])

st.caption("ℹ️ *Shift Pagi (06.00 - 18.00) | Shift Malam (18.00 - 06.00)*")
st.markdown("---")

# 3. Verifikasi Lokasi Geofencing
st.subheader("2. Verifikasi Lokasi Geofencing")
st.info("Klik tombol di bawah ini untuk mengambil titik koordinat GPS Anda.")
lokasi = streamlit_geolocation()

user_lat, user_lng = None, None
jarak = None
posisi_valid = False

if lokasi and lokasi.get('latitude') and lokasi.get('longitude'):
    user_lat = lokasi['latitude']
    user_lng = lokasi['longitude']
    jarak = calculate_distance(OFFICE_LAT, OFFICE_LNG, user_lat, user_lng)
    
    st.write(f"🗺️ **Koordinat Anda:** `{user_lat}, {user_lng}`")
    st.write(f"📏 **Jarak ke Kantor:** `{jarak:.2f} meter`")
    
    if jarak <= MAX_RADIUS_METERS:
        st.success("✅ Lokasi Valid. Anda berada di dalam area kantor.")
        posisi_valid = True
    else:
        st.error(f"❌ Lokasi Ditolak. Anda berada di luar radius izin (Maks {MAX_RADIUS_METERS}m).")

st.markdown("---")

# 4. Bukti Foto Kamera
st.subheader("3. Bukti Kehadiran (Foto Kamera)")
st.warning("Untuk mencegah manipulasi lokasi, wajib ambil foto selfie secara langsung.")
foto_selfie = st.camera_input("Ambil Foto Kamera")

st.markdown("---")

# 5. Tombol Simpan Presensi
if st.button("💾 Simpan Presensi", type="primary", use_container_width=True):
    if not nip_input or not nama_pegawai:
        st.error("Gagal: Masukkan NIP pegawai yang terdaftar.")
    elif user_lat is None or user_lng is None:
        st.error("Gagal: Mohon ambil titik lokasi GPS terlebih dahulu.")
    elif not posisi_valid:
        st.error(f"Gagal: Lokasi ditolak. Jarak Anda ({jarak:.1f} m) melebihi batas {MAX_RADIUS_METERS} m.")
    elif foto_selfie is None:
        st.error("Gagal: Wajib mengambil foto selfie menggunakan kamera.")
    else:
        with st.spinner("Mengunggah foto ke Google Drive & Menyimpan Data..."):
            waktu_sekarang = datetime.now()
            str_waktu = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
            status_waktu = hitung_status_waktu(shift, jenis_absen, waktu_sekarang)
            
            # 1. Unggah foto langsung ke Google Drive
            nama_file_foto = f"{nip_input}_{jenis_absen}_{waktu_sekarang.strftime('%Y%m%d_%H%M%S')}.jpg"
            bytes_foto = foto_selfie.getvalue()
            link_gdrive = upload_to_gdrive(bytes_foto, nama_file_foto)
            
            if link_gdrive:
                # 2. Simpan Link Google Drive ke Database
                with sqlite3.connect('absensi.db') as conn:
                    c = conn.cursor()
                    c.execute('''INSERT INTO presensi 
                                 (nip, nama, shift, jenis_absen, waktu, status_waktu, foto_path) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (nip_input, nama_pegawai, shift, jenis_absen, str_waktu, status_waktu, link_gdrive))
                    conn.commit()
                    
                if status_waktu == "Terlambat":
                    st.warning(f"⚠️ Presensi {jenis_absen} Tercatat pada {str_waktu}. Status: **TERLAMBAT**.")
                else:
                    st.success(f"🎉 Presensi {jenis_absen} Berhasil! Tercatat pada {str_waktu}. Status: **{status_waktu.upper()}**.")
            else:
                st.error("Presensi gagal disimpan karena foto gagal terunggah ke Google Drive.")

# ==========================================
# DASHBOARD REKAP ABSENSI EXCEL (KHUSUS ADMIN)
# ==========================================
st.markdown("---")
with st.expander("📊 Rekap Absensi & Laporan Excel (Khusus Admin)"):
    with sqlite3.connect('absensi.db') as conn:
        df = pd.read_sql_query("SELECT nip AS NIP, nama AS [Nama Pegawai], shift AS Shift, jenis_absen AS [Jenis Presensi], waktu AS [Waktu Presensi], status_waktu AS [Status Waktu], foto_path AS [Link Foto GDrive] FROM presensi ORDER BY id DESC", conn)
        
        if not df.empty:
            list_nip = ["Semua NIP"] + list(df['NIP'].unique())
            pilihan_nip = st.selectbox("Filter Tampilan Berdasarkan NIP:", list_nip)
            
            if pilihan_nip != "Semua NIP":
                df_filtered = df[df['NIP'] == pilihan_nip]
            else:
                df_filtered = df
                
            st.dataframe(df_filtered, use_container_width=True)
            
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Rekap Presensi')
            excel_data = output_excel.getvalue()
            
            nama_file_excel = f"rekap_absensi_{pilihan_nip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            st.download_button(
                label=f"📥 Download Rekap Excel (.xlsx) - {pilihan_nip}",
                data=excel_data,
                file_name=nama_file_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
        else:
            st.info("Belum ada data presensi yang tersimpan di database.")
