Peta Indonesia di PostGIS
=========================

Tulisan ini berisi cara mendapatkan peta Indonesia, termasuk cara
menyempurnakannya. Jika ingin langsung restore ke Postgres silakan `unduh
<https://warga.web.id/files/indonesia/download.html>`_ hasil akhirnya.

Tahapan-tahapannya sudah dicoba di Ubuntu 24.04.

Siapkan PostgreSQL::

    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    sudo apt update
    sudo apt install postgresql-18 postgresql-18-postgis-3

Buat database::

    sudo su - postgres
    createuser -P sugiana
    createdb -O sugiana indonesia
    psql indonesia -c "CREATE EXTENSION postgis"
    psql indonesia -c "CREATE EXTENSION pg_trgm"
    exit

Buat Python virtual environment::

    python3 -m venv ~/env
    ~/env/bin/pip install -U pip
    ~/env/bin/pip install -r requirements.txt

Buat salinan file konfigurasi::

    cp wilayah.ini live.ini

Sesuaikan ``live.ini``. Jalankan proses unduh kode dan nama wilayah dari situs
Dukcapil::

    ~/env/bin/python init_db.py live.ini

Selanjutnya menyimpan multi polygon desa di field ``batas``::

    ~/env/bin/python batas.py live.ini

Adapun batas wilayah untuk tingkat di atasnya diperlukan SQL function::

    psql indonesia -f sql/func_gabung.sql

Kecamatan adalah gabungan kelurahan, dia adalah daerah tingkat 3::

    psql indonesia -c "SELECT gabung(3)"

Lanjut kabupaten::

    psql indonesia -c "SELECT gabung(2)"

Terakhir provinsi::

    psql indonesia -c "SELECT gabung(1)"

Ketiganya ada di file ``sql/gabung.sql``.


Desa menjadi Kelurahan
----------------------

Script ``init_db.py`` secara default akan mengawali field ``nama_lengkap``
untuk **daerah tingkat 4** (desa / kelurahan) dengan ketentuan berikut:

1. Bila terdaftar di ``data/desa_jadi_kelurahan.csv`` maka berawalan
   ``Kelurahan``, contoh:

    field ``key`` = ``32.01.13.1007`` nama lengkap sebelumnya:

    ``Desa Pabuaran, Bojonggede, Kabupaten Bogor, Jawa Barat``

    menjadi

    ``Kelurahan Pabuaran, Bojonggede, Kabupaten Bogor, Jawa Barat``

2. Bila daerah tingkat 2 (kabupaten / kota) berawalan ``Kota`` maka daerah
   tingkat 4-nya berawalan ``Kelurahan``.

3. Selain itu berawalan ``Desa``.

Jika kamu menemukan desa yang ternyata kelurahan maka daftarkanlah di file CSV
itu. Lalu jalankan::

    ~/env/bin/python desa_jadi_kelurahan.py live.ini 

Selama ini bagaimana mendapatkannya ?

Kita bisa mengingat-ingat mana saja kabupaten yang merupakan satelit kota
besar, misalnya Kabupaten Cirebon. Lalu:

1. Google dengan kata kunci: ``wiki kabupaten cirebon``.
2. Bukalah halamannya: ``https://id.wikipedia.org/wiki/Kabupaten_Cirebon``.
3. Tekan Ctrl F untuk mencari kata ``kelurahan``.
4. Nanti ada suatu tabel dengan barisnya berawalan kode kecamatan seperti
   ``32.09.15``. Di kolom terakhirnya tertulis nama-nama kelurahan.
5. Kalau kecamatan itu hanya ada kelurahan maka file CSV cukup ditambahkan dengan::

    32.09,15,"keterangan tidak wajib diisi"

6. Namun kalau tidak semuanya kelurahan maka kita cari dulu kodenya menggunakan
   ``psql``::

    \COPY (SELECT key, nama_lengkap FROM wilayah WHERE key LIKE '32.09.15.%' AND nama = 'Kenanga') TO STDOUT CSV

   hasilnya::

    32.09.15.1014,"Desa Kenanga, Kecamatan Sumber, Kabupaten Cirebon, Provinsi Jawa Barat"

7. Tambahkan di file CSV::

    32.09.15.1014,"Desa Kenanga, Kecamatan Sumber, Kabupaten Cirebon, Provinsi Jawa Barat"

   Field keterangan meski tidak wajib tapi sebaiknya diisi untuk memudahkan
   dalam membaca dokumentasi.

8. Jalankan script tadi::

    ~/env/bin/python desa_jadi_kelurahan.py live.ini

   hasilnya::

    Desa Kenanga, Kecamatan Sumber, Kabupaten Cirebon, Provinsi Jawa Barat ->
    Kelurahan Kenanga, Kecamatan Sumber, Kabupaten Cirebon, Provinsi Jawa Barat


Berikut cara otomatisnya:

1. Unduh::

    ~/env/bin/python wiki_scraper.py https://id.wikipedia.org/wiki/Kabupaten_Cirebon

   Hasilnya file ``wiki.json`` berisi kode kecamatan dan nama-nama kelurahannya.

2. Simpan ke CSV::

    ~/env/bin/python wiki_to_kelurahan_csv.py live.ini >> data/desa_jadi_kelurahan.csv

3. Jalankan script perbaikan::

    ~/env/bin/python desa_jadi_kelurahan.py live.ini

Perlu diketahui bahwa tidak semua halaman Wiki yang terkait wilayah Indonesia
memiliki struktur yang dipahami ``wiki_scrapper.py``. Dengan memahami cara
manual maka kita tahu harus bagaimana. Misalnya minta bantuan
`Google Antigravity <https://antigravity.google>`_ untuk membuatkan script-nya.


Tampilkan di Web
----------------

Untuk menampilkannya di web maka kita membutuhkan web server::

    sudo apt install nginx

Misalkan akan ditampilkan sebuah **kawasan** maka carilah kode wilayahnya di tabel ``wilayah``, contoh::

    SELECT key, nama FROM wilayah WHERE nama ~ 'Rangkapan Jaya';

Hasilnya::

          key      |        nama
    ---------------+---------------------
     32.76.01.1011 | Rangkapan Jaya
     32.76.01.1010 | Rangkapan Jaya Baru

Sertakan keduanya dalam sebuah file Geo JSON::

    ~/env/bin/python db_to_geojson.py live.ini 32.76.01.1011 32.76.01.1010 > kawasan.geojson

Buat file HTML-nya::

    ~/env/bin/python geojson_to_html.py kawasan.geojson

Hasilnya::

    File kawasan.html sudah dibuat.

Salin kedua file itu ke direktori web server::

    sudo cp kawasan.* /var/www/html/

Di web browser buka ``http://localhost/kawasan.html``.


Referensi
---------

1. `Kabupaten Bogor <https://id.wikipedia.org/wiki/Kabupaten_Bogor>`_
2. `Kabupaten Cirebon <https://id.wikipedia.org/wiki/Kabupaten_Cirebon>`_
3. `Kabupaten Tangerang <https://id.wikipedia.org/wiki/Kabupaten_Tangerang>`_
4. `Kabupaten Bekasi <https://id.wikipedia.org/wiki/Kabupaten_Bekasi>`_
5. `Kabupaten Lebak <https://id.wikipedia.org/wiki/Kabupaten_Lebak>`_
6. `Kabupaten Sukabumi <https://id.wikipedia.org/wiki/Kabupaten_Sukabumi>`_
7. `Kabupaten Cianjur <https://id.wikipedia.org/wiki/Kabupaten_Cianjur>`_
8. `Kabupaten Bandung <https://id.wikipedia.org/wiki/Kabupaten_Bandung>`_
9. `Kabupaten Garut <https://id.wikipedia.org/wiki/Kabupaten_Garut>`_
10. `Kabupaten Ciamis <https://id.wikipedia.org/wiki/Kabupaten_Ciamis>`_
11. `Kabupaten Kuningan <https://id.wikipedia.org/wiki/Kabupaten_Kuningan>`_
12. `Kabupaten Majalengka <https://id.wikipedia.org/wiki/Kabupaten_Majalengka>`_
13. `Kabupaten Sumedang <https://id.wikipedia.org/wiki/Kabupaten_Sumedang>`_
14. `Kabupaten Indramayu <https://id.wikipedia.org/wiki/Kabupaten_Indramayu>`_
15. `Kabupaten Subang <https://id.wikipedia.org/wiki/Kabupaten_Subang>`_
16. `Kabupaten Purwakarta <https://id.wikipedia.org/wiki/Kabupaten_Purwakarta>`_
17. `Kabupaten Karawang <https://id.wikipedia.org/wiki/Kabupaten_Karawang>`_
18. `Kabupaten Pandeglang <https://id.wikipedia.org/wiki/Kabupaten_Pandeglang>`_
19. `Kabupaten Tolikara <https://en.wikipedia.org/wiki/Tolikara_Regency>`_
20. `Kabupaten Musi Rawas <https://id.wikipedia.org/wiki/Kabupaten_Musi_Rawas>`_
21. `Daftar distrik dan kampung di Kabupaten Raja Ampat <https://id.wikipedia.org/wiki/Daftar_distrik_dan_kampung_di_Kabupaten_Raja_Ampat>`_
22. `Kabupaten Aceh Tenggara <https://id.wikipedia.org/wiki/Kabupaten_Aceh_Tenggara>`_
23. `Kabupaten Aceh Timur <https://id.wikipedia.org/wiki/Kabupaten_Aceh_Timur>`_
24. `Lhoknga, Aceh Besar <https://id.wikipedia.org/wiki/Lhoknga,_Aceh_Besar>`_
25. `Leupung, Aceh Besar <https://id.wikipedia.org/wiki/Leupung,_Aceh_Besar>`_
26. `Kabupaten Pidie <https://id.wikipedia.org/wiki/Kabupaten_Pidie>`_
27. `Teungku Dibanda Tektek <https://id.wikipedia.org/wiki/Teungku_Dibanda_Tektek,_Paya_Bakong,_Aceh_Utara>`_
28. `Teungku Dibanda Pirak <https://id.wikipedia.org/wiki/Teungku_Dibanda_Pirak,_Paya_Bakong,_Aceh_Utara>`_
29. `Teungku Di Bathon <https://id.wikipedia.org/wiki/Teungku_Di_Bathon,_Peudada,_Bireuen>`_
30. `Matang Glumpang II Meunasah Timur, Peusangan, Bireuen <https://id.wikipedia.org/wiki/Matang_Glumpang_II_Meunasah_Timur,_Peusangan,_Bireuen>`_
31. `Perkebunan Gedung Biara, Seruway, Aceh Tamiang <https://id.wikipedia.org/wiki/Perkebunan_Gedung_Biara,_Seruway,_Aceh_Tamiang>`_
32. `Gelampang Wih Tenang Uken, Permata, Bener Meriah <https://id.wikipedia.org/wiki/Gelampang_Wih_Tenang_Uken,_Permata,_Bener_Meriah>`_
33. `Meunasah Panggoi <https://www.wikidata.org/wiki/Q18709915>`_
34. `Pelatihan Peningkatan Kapasitas Aparatur pemerintahan Gampong <https://pbbeuramo.gampong.id/berita/kategori/berita/pelatihan-peningkatan-kapasitas-aparatur-pemerintahan-gampong>`_
35. `Paya Bujok Teungoh, Langsa Barat, Langsa <https://id.wikipedia.org/wiki/Paya_Bujok_Teungoh,_Langsa_Barat,_Langsa>`_
36. `Pasar Onan Manduamas, Manduamas, Tapanuli Tengah <https://id.wikipedia.org/wiki/Pasar_Onan_Manduamas,_Manduamas,_Tapanuli_Tengah>`_
37. `Pasar Onan Hurlang, Kolang, Tapanuli Tengah <https://id.wikipedia.org/wiki/Pasar_Onan_Hurlang,_Kolang,_Tapanuli_Tengah>`_
38. `Tapian Nauli Saur Manggita, Tukka, Tapanuli Tengah <https://id.wikipedia.org/wiki/Tapian_Nauli_Saur_Manggita,_Tukka,_Tapanuli_Tengah>`_
39. `Pardomuan Janji Angkola, Purba Tua, Tapanuli Utara <https://id.wikipedia.org/wiki/Pardomuan_Janji_Angkola,_Purba_Tua,_Tapanuli_Utara>`_
40. `Parsaoran Janji Angkola, Purba Tua, Tapanuli Utara <https://id.wikipedia.org/wiki/Parsaoran_Janji_Angkola,_Purba_Tua,_Tapanuli_Utara>`_
41. `Lalai I/II, Hiliserangkai, Nias <https://id.wikipedia.org/wiki/Lalai_I/II,_Hiliserangkai,_Nias>`_
42. `Perkebunan Bukit Lawang, Bahorok, Langkat <https://id.wikipedia.org/wiki/Perkebunan_Bukit_Lawang,_Bahorok,_Langkat>`_
43. `Lubuk Pakam I, II, Lubuk Pakam, Deli Serdang <https://id.wikipedia.org/wiki/Lubuk_Pakam_I,_II,_Lubuk_Pakam,_Deli_Serdang>`_
44. `Perkebunan Air Batu I–II, Air Batu, Asahan <https://id.wikipedia.org/wiki/Perkebunan_Air_Batu_I%E2%80%93II,_Air_Batu,_Asahan>`_
45. `Perkebunan Air Batu III–IV, Air Batu, Asahan <https://id.wikipedia.org/wiki/Perkebunan_Air_Batu_III%E2%80%93IV,_Air_Batu,_Asahan>`_
46. `Perkebunan Afdeling I Rantau Prapat, Bilah Barat, Labuhanbatu <https://id.wikipedia.org/wiki/Perkebunan_Afdeling_I_Rantau_Prapat,_Bilah_Barat,_Labuhanbatu>`_
47. `Sibarani Nasampulu, Laguboti, Toba <https://id.wikipedia.org/wiki/Sibarani_Nasampulu,_Laguboti,_Toba>`_
48. `Muara Batang Angkola, Siabu, Mandailing Natal <https://id.wikipedia.org/wiki/Muara_Batang_Angkola,_Siabu,_Mandailing_Natal>`_
49. `Perkebunan Simpang Gambir, Lingga Bayu, Mandailing Natal <https://id.wikipedia.org/wiki/Perkebunan_Simpang_Gambir,_Lingga_Bayu,_Mandailing_Natal>`_
50. `Tanjung Baru Silaiya, Dolok Sigompulon, Padang Lawas Utara <https://id.wikipedia.org/wiki/Tanjung_Baru_Silaiya,_Dolok_Sigompulon,_Padang_Lawas_Utara>`_
51. `Pp Makmur, Barumun Tengah, Padang Lawas <https://id.wikipedia.org/wiki/Pp_Makmur,_Barumun_Tengah,_Padang_Lawas>`_
52. `Perkebunan Sei Rumbia, Kotapinang, Labuhanbatu Selatan <https://id.wikipedia.org/wiki/Perkebunan_Sei_Rumbia,_Kotapinang,_Labuhanbatu_Selatan>`_
53. `Sei Rengas Permata, Medan Area, Medan <https://id.wikipedia.org/wiki/Sei_Rengas_Permata,_Medan_Area,_Medan>`_
54. `Selayo Tanang Bukit Sileh, Lembang Jaya, Solok <https://id.wikipedia.org/wiki/Selayo_Tanang_Bukit_Sileh,_Lembang_Jaya,_Solok>`_
55. `Kecamatan Ilir Timur Satu <https://kec-ilirtimursatu.palembang.go.id/kelurahan>`_
56. `SD INPRES KADAM OYIM <https://sekolah.data.kemendikdasmen.go.id/profil-sekolah/405BB940-31F5-E011-ACF4-C5A9872236AD>`_
57. `SD YPPK YOHANES PERMANDI TAIM <https://sekolah.data.kemendikdasmen.go.id/profil-sekolah/40191041-31F5-E011-9C66-F3A234A1E532>`_
58. `SD YPPK STA. AGNES AMBOREP <https://referensi.data.kemendikdasmen.go.id/pendidikan/npsn/60303641>`_
59. `Menyelamatkan Ibu Hamil dan Anak-anak di Asmat <https://www.kompas.id/artikel/menyelamatkan-ibu-hamil-dan-anak-anak-di-asmat>`_
