SELECT sum(data['jumlah_penduduk']::int) AS jumlah_penduduk
    FROM wilayah
    WHERE tingkat_id = 4;
