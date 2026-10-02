# SOP Database Recovery v1

## Bagian 1: Tujuan
SOP ini mengatur pemulihan database PostgreSQL SIMRS setelah kerusakan atau kehilangan data.

## Bagian 2: Prasyarat Pemulihan
Pastikan backup database terakhir valid dan WAL archive tersedia sebelum pemulihan dimulai.

## Bagian 3: Prosedur Pemulihan Database
Prosedur pemulihan database: 1. Hentikan aplikasi. 2. Restore base backup. 3. Replay WAL sampai titik waktu target. 4. Verifikasi integritas tabel. 5. Aktifkan kembali aplikasi.

## Bagian 4: Validasi Pasca Pemulihan
Tim aplikasi memverifikasi data transaksi 24 jam terakhir sebelum layanan dibuka.
