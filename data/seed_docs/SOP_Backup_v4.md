# SOP Backup Server v4

## Bagian 1: Tujuan dan Ruang Lingkup
SOP ini mengatur backup server produksi rumah sakit agar data klinis dan administrasi dapat dipulihkan. Mode pelaksanaan: otomatis penuh. Penanggung jawab backup server adalah Administrator Infrastruktur.

## Bagian 2: Jadwal Backup
Backup penuh setiap Minggu pukul 01.00, inkremental harian pukul 23.00, dan snapshot database setiap 6 jam. Perubahan jadwal backup server harus disetujui Kepala IT.

## Bagian 3: Prosedur Backup Server
Prosedur backup server menggunakan Bareos + replikasi offsite ke object storage. Langkah prosedur backup server:
1. Sistem Bareos menjalankan job backup otomatis lalu mereplikasi hasilnya ke object storage offsite.
2. Sistem monitoring memvalidasi checksum setiap job dan mengirim alert bila gagal.
3. Petugas jaga mengonfirmasi laporan harian dan membuat tiket hanya bila ada anomali.

## Bagian 4: Retensi dan Penyimpanan
Retensi backup server adalah 90 hari. Backup yang melewati masa retensi dihapus secara terjadwal.

## Bagian 5: Verifikasi dan Restore Test
Restore test otomatis dilakukan setiap bulan dan hasilnya dilaporkan ke Kepala IT. Hasil verifikasi backup dicatat dan ditandatangani Kepala IT.

## Bagian 6: Enkripsi dan Keamanan Backup
Enkripsi AES-256 pada data diam dan TLS 1.3 pada transfer; kunci disimpan di vault. Akses ke media backup dibatasi untuk administrator berwenang.
