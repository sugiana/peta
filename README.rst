Peta Indonesia di PostGIS
=========================

Tulisan ini berisi cara mendapatkan peta Indonesia, termasuk cara
menyempurnakannya. Jika ingin langsung restore ke Postgres silakan `unduh
<https://warga.web.id/files/indonesia/download.html>`_ hasil akhirnya.

Tahapan-tahapannya sudah dicoba di Ubuntu 24.04.

Siapkan MariaDB untuk restore database sumber::

    sudo apt install mariadb-server libmariadb-dev

Buat database::

    sudo mysql
    CREATE USER sugiana IDENTIFIED BY 'R4hasia';
    CREATE DATABASE indonesia;
    GRANT ALL PRIVILEGES ON indonesia.* TO sugiana;
    EXIT

Unduh file sumbernya::

    git clone https://github.com/cahyadsn/wilayah

Restore::

    mysql -u sugiana -p indonesia < wilayah/db/wilayah.sql

Siapkan PostgreSQL untuk targetnya::

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

Sesuaikan ``live.ini``. Jalankan penyalinan kode dan nama::

    ~/env/bin/python init_db.py live.ini

Lalu menyimpan batas wilayah dan statistik desa dari Dukcapil::

    psql indonesia -f sql/func_gabung.sql
    ~/env/bin/python perbarui_data live.ini

Ini ada proses unduh dari ``https://gis.dukcapil.kemendagri.go.id/peta`` untuk
setiap kecamatan. Butuh waktu sekitar tiga jam. Nanti akan tampak perkiraannya. 


Desa menjadi Kelurahan
----------------------

Script ``init_db.py`` secara default akan mengawali field ``nama_lengkap``
untuk **daerah tingkat 4** (desa / kelurahan) dengan ketentuan berikut:

1. Bila terdaftar di ``data/desa_jadi_kelurahan.csv`` maka berawalan ``Kelurahan``, contoh:

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

6. Namun kalau tidak semuanya kelurahan maka kita cari dulu kodenya menggunakan ``psql``::

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


Unduh Ulang Geo JSON
--------------------

Jika ada perubahan di sumber asli Geo JSON maka perlu diunduh ulang. Untuk itu
diperlukan web browser Google Chrome. Lalu pasang pasang paket yang dibutuhkan::

    ~/env/bin/pip install selenium webdriver-manager

Mulai unduh Jakarta misalnya::

    ~/env/bin/python petanusa.py 31

``31`` adalah kode Provinsi Jakarta. Daftarnya bisa lihat di ``data/provinsi.csv``.

Atau tanpa menyebutkan kode provinsi untuk mengunduh semua provinsi.

Kemudian jalankan lagi penyimpanan ke database::

    ~/env/bin/python geojson_to_db.py live.ini


Desa Lalemo
-----------

Ini adalah perjalanan bagaimana *repository* ini dibuat.

Kita berangkat dari `CahyaDSN <https://github.com/cahyadsn/wilayah>`_ dengan
`wilayah.sql <https://github.com/cahyadsn/wilayah/blob/master/db/wilayah.sql>`_
yang bersumber dari keputusan
`Menteri Dalam Negeri 25 April 2025 <https://jdih.kemendagri.go.id/dokumen/view?id=1937>`_.
Silakan `unduh lampirannya <https://drive.google.com/file/d/1o_m621D00TtwCwQMLn8XUnV3nolamPDm/view>`_.

Tidak ada data **statistik desa** di dalamnya sehingga perlu diunduh dari web GIS
Dukcapil oleh ``perbaiki_data.py``. Data yang dimaksud contohnya jumlah
penduduk, jumlah pria, jumlah wanita, dst.

Untuk menghemat waktu *web request* maka diputuskan mengambil data per
kecamatan yang nantinya tampil seluruh desanya. Di sini masalah mulai muncul,
ia berhenti dengan pesan kesalahan berikut:: 

    72.06.06.2018 Desa LALEMO, BUNGKU SELATAN, KAB. MOROWALI, SULAWESI TENGAH belum terdaftar.

Untuk memastikannya maka dicarilah kata ``Lalemo`` di PDF Menteri 2025 itu.
Dengan menekan Ctrl F di PDF viewer dan mengetikkan apa yang mau dicari
akhirnya ditemukan di kode kecamatan ``72.06.06`` **tapi tidak ada kode desa**.
Di atasnya ada kode desa, tapi di bawahnya ada 22 desa lagi yang tak berkode.

Karena penasaran maka dicarilah di CahyaDSN direktori
`archive <https://github.com/cahyadsn/wilayah/tree/master/db/archive>`_::

    grep -i lalemo *.sql

hasilnya::

    wilayah_2016.sql:("72.06.06.2018","Lalemo"),
    wilayah_2018.sql:('72.06.06.2018','Lalemo'),
    wilayah_2020.sql:('72.06.06.2018', 'Lalemo'),
    wilayah_2022.sql:('72.06.06.2018','Lalemo'),
    wilayah_2023.sql:('72.06.06.2018','Lalemo'),

Ternyata sudah lama ada.

CahyaDSN memberikan pilihan, *repo* ini telah memilih.


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
