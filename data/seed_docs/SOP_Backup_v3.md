# SOP Backup Server v3

## Bagian 1: Tujuan dan Ruang Lingkup
SOP ini mengatur backup server produksi rumah sakit agar data klinis dan administrasi dapat dipulihkan. Mode pelaksanaan: otomatis sebagian. Penanggung jawab backup server adalah Administrator Infrastruktur.

## Bagian 2: Jadwal Backup
Backup penuh setiap Minggu pukul 01.00 dan backup inkremental harian pukul 23.00. Perubahan jadwal backup server harus disetujui Kepala IT.

## Bagian 3: Prosedur Backup Server
Prosedur backup server menggunakan Bareos dengan penjadwalan terpusat. Langkah prosedur backup server:
1. Bareos menjalankan job backup server sesuai jadwal.
2. Administrator meninjau laporan job backup server setiap pagi.
3. Kegagalan job dilaporkan melalui email ke tim infrastruktur.

## Bagian 4: Retensi dan Penyimpanan
Retensi backup server adalah 60 hari. Backup yang melewati masa retensi dihapus secara terjadwal.

## Bagian 5: Verifikasi dan Restore Test
Restore test dilakukan setiap 3 bulan sekali. Hasil verifikasi backup dicatat dan ditandatangani Kepala IT.

## Bagian 6: Enkripsi dan Keamanan Backup
Enkripsi AES-128 pada transfer ke NAS. Akses ke media backup dibatasi untuk administrator berwenang.
