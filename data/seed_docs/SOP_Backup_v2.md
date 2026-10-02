# SOP Backup Server v2

## Bagian 1: Tujuan dan Ruang Lingkup
SOP ini mengatur backup server produksi rumah sakit agar data klinis dan administrasi dapat dipulihkan. Mode pelaksanaan: semi-manual. Penanggung jawab backup server adalah Administrator Infrastruktur.

## Bagian 2: Jadwal Backup
Backup penuh setiap Minggu pukul 01.00 dan backup harian manual oleh administrator. Perubahan jadwal backup server harus disetujui Kepala IT.

## Bagian 3: Prosedur Backup Server
Prosedur backup server menggunakan rsync ke NAS lokal. Langkah prosedur backup server:
1. Administrator menjalankan script rsync untuk backup server ke NAS lokal.
2. Administrator memeriksa log rsync dan mencatat hasil prosedur backup server pada tiket.
3. Salinan backup server disimpan di NAS lokal selama masa retensi.

## Bagian 4: Retensi dan Penyimpanan
Retensi backup server adalah 30 hari. Backup yang melewati masa retensi dihapus secara terjadwal.

## Bagian 5: Verifikasi dan Restore Test
Restore test dilakukan setiap 6 bulan sekali. Hasil verifikasi backup dicatat dan ditandatangani Kepala IT.

## Bagian 6: Enkripsi dan Keamanan Backup
Enkripsi opsional menggunakan GPG pada file tertentu. Akses ke media backup dibatasi untuk administrator berwenang.
