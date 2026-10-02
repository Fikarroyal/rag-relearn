# SOP Backup Server v1

## Bagian 1: Tujuan dan Ruang Lingkup
SOP ini mengatur backup server produksi rumah sakit agar data klinis dan administrasi dapat dipulihkan. Mode pelaksanaan: manual. Penanggung jawab backup server adalah Administrator Infrastruktur.

## Bagian 2: Jadwal Backup
Backup dilakukan setiap hari Jumat sore secara manual. Perubahan jadwal backup server harus disetujui Kepala IT.

## Bagian 3: Prosedur Backup Server
Prosedur backup server menggunakan salin manual ke hard disk eksternal. Langkah prosedur backup server:
1. Administrator menyalin folder data server ke hard disk eksternal.
2. Administrator mencatat tanggal backup pada buku log.
3. Hard disk disimpan di lemari ruang server.

## Bagian 4: Retensi dan Penyimpanan
Retensi backup server adalah 14 hari. Backup yang melewati masa retensi dihapus secara terjadwal.

## Bagian 5: Verifikasi dan Restore Test
Restore test dilakukan hanya jika terjadi insiden. Hasil verifikasi backup dicatat dan ditandatangani Kepala IT.

## Bagian 6: Enkripsi dan Keamanan Backup
Tidak ada enkripsi pada media backup. Akses ke media backup dibatasi untuk administrator berwenang.
