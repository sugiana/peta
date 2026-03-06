Peta Indonesia di PostGIS
=========================

Tulisan ini berisi cara mendapatkan peta Indonesia, termasuk cara
menyempurnakannya. Jika ingin langsung restore ke Postgres silakan `unduh
<https://warga.web.id/files/indonesia/download.html>`_ hasil akhirnya.

Tahapan-tahapannya sudah dicoba di Ubuntu 24.04.

Unduh
`PDF sumbernya <https://drive.google.com/file/d/1o_m621D00TtwCwQMLn8XUnV3nolamPDm/view>`_.
Ubah namanya agar tidak mengandung spasi sehingga lebih nyaman dilihat:
``kepmendagri-nomor-300.2.2-2138-tahun-2025001.pdf``.

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

    cp contoh.ini live.ini

Sesuaikan ``live.ini``. Jalankan penyalinan kode dan nama::

    ~/env/bin/python init_db.py live.ini kepmendagri-nomor-300.2.2-2138-tahun-2025001.pdf

Lalu menyimpan batas wilayah dan statistik desa dari Dukcapil::

    psql indonesia -f sql/func_gabung.sql
    ~/env/bin/python perbarui_data live.ini

Ini ada proses unduh dari ``https://gis.dukcapil.kemendagri.go.id/peta`` untuk
setiap kecamatan. Butuh waktu sekitar tiga jam. Nanti akan tampak perkiraannya. 


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

Cara lainnya adalah membuat web server yang langsung membaca dari database
Postgres. Kita bisa gunakan `Web Peta <https://github.com/sugiana/web-peta>`_.
