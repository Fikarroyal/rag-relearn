"""Membuat dokumen SOP demo (Markdown). SOP_Backup v1-v4 sengaja sangat mirip tetapi prosedurnya berbeda."""

from __future__ import annotations
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "seed_docs"
OUT.mkdir(parents=True, exist_ok=True)

BACKUP = {
    1: dict(tool="salin manual ke hard disk eksternal", jadwal="Backup dilakukan setiap hari Jumat sore secara manual.", ret=14, enc="Tidak ada enkripsi pada media backup.", verif="Restore test dilakukan hanya jika terjadi insiden.", auto="manual",
            steps=["Administrator menyalin folder data server ke hard disk eksternal.", "Administrator mencatat tanggal backup pada buku log.", "Hard disk disimpan di lemari ruang server."]),
    2: dict(tool="rsync ke NAS lokal", jadwal="Backup penuh setiap Minggu pukul 01.00 dan backup harian manual oleh administrator.", ret=30, enc="Enkripsi opsional menggunakan GPG pada file tertentu.", verif="Restore test dilakukan setiap 6 bulan sekali.", auto="semi-manual",
            steps=["Administrator menjalankan script rsync untuk backup server ke NAS lokal.", "Administrator memeriksa log rsync dan mencatat hasil prosedur backup server pada tiket.", "Salinan backup server disimpan di NAS lokal selama masa retensi."]),
    3: dict(tool="Bareos dengan penjadwalan terpusat", jadwal="Backup penuh setiap Minggu pukul 01.00 dan backup inkremental harian pukul 23.00.", ret=60, enc="Enkripsi AES-128 pada transfer ke NAS.", verif="Restore test dilakukan setiap 3 bulan sekali.", auto="otomatis sebagian",
            steps=["Bareos menjalankan job backup server sesuai jadwal.", "Administrator meninjau laporan job backup server setiap pagi.", "Kegagalan job dilaporkan melalui email ke tim infrastruktur."]),
    4: dict(tool="Bareos + replikasi offsite ke object storage", jadwal="Backup penuh setiap Minggu pukul 01.00, inkremental harian pukul 23.00, dan snapshot database setiap 6 jam.", ret=90, enc="Enkripsi AES-256 pada data diam dan TLS 1.3 pada transfer; kunci disimpan di vault.", verif="Restore test otomatis dilakukan setiap bulan dan hasilnya dilaporkan ke Kepala IT.", auto="otomatis penuh",
            steps=["Sistem Bareos menjalankan job backup otomatis lalu mereplikasi hasilnya ke object storage offsite.", "Sistem monitoring memvalidasi checksum setiap job dan mengirim alert bila gagal.", "Petugas jaga mengonfirmasi laporan harian dan membuat tiket hanya bila ada anomali."]),
}


def backup_doc(v, d):
    steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(d["steps"]))
    return f"""# SOP Backup Server v{v}

## Bagian 1: Tujuan dan Ruang Lingkup
SOP ini mengatur backup server produksi rumah sakit agar data klinis dan administrasi dapat dipulihkan. Mode pelaksanaan: {d['auto']}. Penanggung jawab backup server adalah Administrator Infrastruktur.

## Bagian 2: Jadwal Backup
{d['jadwal']} Perubahan jadwal backup server harus disetujui Kepala IT.

## Bagian 3: Prosedur Backup Server
Prosedur backup server menggunakan {d['tool']}. Langkah prosedur backup server:
{steps}

## Bagian 4: Retensi dan Penyimpanan
Retensi backup server adalah {d['ret']} hari. Backup yang melewati masa retensi dihapus secara terjadwal.

## Bagian 5: Verifikasi dan Restore Test
{d['verif']} Hasil verifikasi backup dicatat dan ditandatangani Kepala IT.

## Bagian 6: Enkripsi dan Keamanan Backup
{d['enc']} Akses ke media backup dibatasi untuk administrator berwenang.
"""


OTHERS = {
    "SOP_Network_Maintenance_v1": ("SOP Network Maintenance", [
        ("Tujuan dan Ruang Lingkup", "SOP ini mengatur pemeliharaan perangkat jaringan: switch, router, access point, dan firewall."),
        ("Jadwal Maintenance Bulanan", "Maintenance jaringan dilakukan setiap bulan pada Sabtu minggu pertama pukul 22.00 dengan pemberitahuan ke seluruh unit 3 hari sebelumnya."),
        ("Langkah Maintenance Jaringan", "Langkah: 1. Backup konfigurasi perangkat. 2. Update firmware secara bertahap. 3. Uji konektivitas antar VLAN. 4. Catat hasil maintenance jaringan pada change log."),
        ("Rollback", "Jika konektivitas terganggu lebih dari 15 menit, lakukan rollback konfigurasi dari backup terakhir.")]),
    "SOP_Incident_Response_v1": ("SOP Incident Response", [
        ("Tujuan dan Klasifikasi", "SOP ini mengatur respon insiden keamanan informasi dengan klasifikasi severity 1 sampai 4."),
        ("Deteksi dan Pelaporan", "Setiap staf wajib melaporkan insiden keamanan ke helpdesk IT maksimal 30 menit setelah diketahui."),
        ("Prosedur Respon Insiden Keamanan", "Prosedur respon insiden: 1. Isolasi sistem terdampak. 2. Kumpulkan bukti log. 3. Eradikasi ancaman. 4. Pulihkan layanan. 5. Tulis laporan pasca insiden dalam 5 hari kerja."),
        ("Eskalasi", "Insiden severity 1 dieskalasi ke Direktur dalam 1 jam.")]),
    "SOP_Database_Recovery_v1": ("SOP Database Recovery", [
        ("Tujuan", "SOP ini mengatur pemulihan database PostgreSQL SIMRS setelah kerusakan atau kehilangan data."),
        ("Prasyarat Pemulihan", "Pastikan backup database terakhir valid dan WAL archive tersedia sebelum pemulihan dimulai."),
        ("Prosedur Pemulihan Database", "Prosedur pemulihan database: 1. Hentikan aplikasi. 2. Restore base backup. 3. Replay WAL sampai titik waktu target. 4. Verifikasi integritas tabel. 5. Aktifkan kembali aplikasi."),
        ("Validasi Pasca Pemulihan", "Tim aplikasi memverifikasi data transaksi 24 jam terakhir sebelum layanan dibuka.")]),
    "SOP_User_Access_v1": ("SOP User Access", [
        ("Tujuan", "SOP ini mengatur pemberian, perubahan, dan pencabutan hak akses pengguna sistem informasi."),
        ("Prosedur Pembuatan Akses Pengguna Baru", "Pembuatan akses pengguna baru: 1. Atasan mengajukan formulir akses. 2. Kepala IT menyetujui. 3. Administrator membuat akun dengan prinsip least privilege. 4. Pengguna mengganti password pertama kali."),
        ("Review Akses", "Review hak akses seluruh pengguna dilakukan setiap 6 bulan oleh Kepala IT."),
        ("Pencabutan Akses", "Akses pengguna yang resign dicabut maksimal 1 hari kerja setelah tanggal efektif.")]),
    "SOP_Security_v1": ("SOP Security", [
        ("Tujuan", "SOP ini mengatur kebijakan keamanan informasi rumah sakit."),
        ("Kebijakan Password", "Password minimal 12 karakter, kombinasi huruf besar, kecil, angka, dan simbol, diganti setiap 90 hari. Multi-factor authentication wajib untuk akses remote."),
        ("Keamanan Perangkat", "Seluruh perangkat wajib memakai antivirus, enkripsi disk, dan patch keamanan maksimal 14 hari setelah rilis."),
        ("Audit Keamanan", "Audit keamanan internal dilakukan setiap kuartal.")]),
}

for v, d in BACKUP.items():
    (OUT / f"SOP_Backup_v{v}.md").write_text(backup_doc(v, d), encoding="utf-8")
for did, (title, secs) in OTHERS.items():
    body = f"# {title} v1\n\n" + "\n\n".join(f"## Bagian {i+1}: {h}\n{t}" for i, (h, t) in enumerate(secs)) + "\n"
    (OUT / f"{did}.md").write_text(body, encoding="utf-8")
print("seed docs:", len(list(OUT.glob('*.md'))))
