# Validasi versi publik

Diperiksa 16 Oktober 2026.

## Data aktual

- Pengambilan API berhasil untuk 656 koordinat grid reguler (16 lintang × 41 bujur).
- Setiap parameter memiliki 72 jam waktu valid; bentuk array 72 × 16 × 41.
- Parameter: PM2.5, PM10, CO, NO₂, SO₂, O₃, US AQI, dan AOD total.
- Interval sampel 1,2°. Pemilihan sel API `nearest`. Pengambilan tidak menggunakan 38 kota sebagai sumber interpolasi peta.
- Cache awal berasal dari API pada 16 Oktober 2026, 02:34 UTC. Aplikasi memeriksa usia dan memperbarui cache sesuai kebijakan enam jam.

## Pemeriksaan yang lolos

- Tujuh unit test: grid 656 koordinat, transparansi nilai hilang, cache atomik, pemakaian cache segar, fallback cache lama, pemilihan sampel kota, konstruksi image overlay, dan pemeriksaan tidak adanya input API pada antarmuka (sebagian kasus digabung dalam satu test).
- Streamlit AppTest: render awal, pilihan AOD, fokus Sumatra, penggantian waktu, analisis wilayah, perbandingan wilayah, serta halaman metode.
- Default waktu memilih jam yang sudah berlaku; tampilan iframe versi Streamlit yang terpasang berhasil dirender pada tingkat komponen.
- JavaScript peta lolos `node --check`.
- Raster warna aktual diperiksa secara visual. Array lintang disusun selatan→utara dan diproyeksikan dengan origin lower untuk image overlay Leaflet.
- Pengaturan API, input password, upload CSV, dan kontrol refresh tidak tersedia bagi pengunjung. Fitur kabut asap hanya kartu Segera hadir.

## Batas pemeriksaan

- Browser end-to-end tidak tersedia: executable Chromium tidak terpasang pada lingkungan pemeriksaan. Interaksi zoom/popup/fullscreen Leaflet dan pemuatan tiles CARTO belum diverifikasi melalui browser; markup, JavaScript, raster, dan komponen Streamlit sudah diperiksa.
- Sampel grid lebih jarang daripada resolusi model asli. Interpolasi bilinear hanya penghalusan tampilan dan bukan peningkatan ketelitian.
- Dashboard memakai data model, bukan jaringan pengamatan stasiun. Prediksi khusus asap kebakaran belum tersedia.
- Paket belum diterbitkan ke hosting publik. Localhost pada laptop hanya dapat diakses sesuai konfigurasi jaringan setempat.

## Perbaikan 16 Oktober: panel internal tercetak

Ekspresi kondisional satu baris untuk iframe diganti blok if/else. Uji regresi memastikan iframe tersedia dan tidak ada elemen doc_string atau code yang menampilkan dokumentasi DeltaGenerator. Delapan pengujian lolos setelah perbaikan.

## Peta pada Analisis wilayah

Peta raster ditambahkan ke halaman Analisis wilayah. Uji komponen memastikan lapisan berubah ketika parameter/waktu diganti, fokus bergeser ke koordinat kota saat wilayah berubah, dan panel internal DeltaGenerator tidak tercetak. Gaya raster dan skala warna menggunakan renderer yang sama dengan Peta sebaran.

## Perbaikan peta kosong

Ditemukan urutan JavaScript yang keliru: handler klik didaftarkan sebelum `L.map()` dijalankan. Handler dipindahkan ke child MacroElement sehingga baru dijalankan setelah inisialisasi dan layer peta. Runtime Leaflet sekarang disertakan sebagai aset lokal. Regresi memeriksa urutan inisialisasi dan tidak adanya script CDN. JavaScript hasil render juga dieksekusi dengan test double Leaflet di Node: peta, image overlay, handler dan popup berhasil. Pemeriksaan ini bukan pengganti uji browser penuh; pemasangan browser pada lingkungan uji tidak berhasil.

## Peta dasar ber-watermark API KEY REQUIRED

Screenshot pengguna memperlihatkan raster sudah dimuat, tetapi dua tile layer CARTO mengembalikan watermark permintaan API key. Keduanya dihapus dan diganti satu tile layer OpenStreetMap HTTPS dengan atribusi. Tinggi map diubah menjadi 100% mengikuti iframe, untuk mencegah scrollbar pada peta regional. Uji komponen dan markup memastikan URL CARTO sudah tidak digunakan. Layanan tile mengikuti kebijakan OSM; tidak dilakukan prefetch atau pemeriksaan tile melalui headless bot.
