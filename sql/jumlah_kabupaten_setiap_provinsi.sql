SELECT prov.key, prov.nama, j.nama, count(*)
    FROM wilayah prov, wilayah kab, jenis_wilayah j
    WHERE prov.id = kab.wilayah_id
        AND kab.jenis_id = j.id
        AND prov.tingkat_id = 1
    GROUP BY 1, 2, 3
    ORDER BY 1, 3;
