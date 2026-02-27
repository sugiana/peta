CREATE OR REPLACE FUNCTION tutup_lubang(geom geometry)
RETURNS geometry
LANGUAGE plpgsql
AS $$
-- Saat penggabungan 2 wilayah kadang membentuk lubang-lubang kecil di
-- dalamnya. Fungsi ini menghilangkannya.
-- Jika MultiPolygon maka kita harus memproses setiap Polygon di dalamnya.
BEGIN
    RETURN ST_Collect(ST_MakePolygon(ST_ExteriorRing(dumped.geom)))
    FROM ST_Dump(geom) AS dumped;
END $$;


CREATE OR REPLACE FUNCTION gabung(p_key text) 
RETURNS VOID 
LANGUAGE plpgsql
AS $$
-- Isi dengan gabungan batas wilayah-wilayah di bawahnya.
DECLARE
    rec record;
    geom geometry;
BEGIN
    SELECT id, nama, tingkat_id
        INTO rec 
        FROM wilayah
        WHERE key = p_key;

    SELECT tutup_lubang(ST_UnaryUnion(ST_Collect(ST_MakeValid(batas))))
        INTO geom
        FROM wilayah
        WHERE wilayah_id = rec.id
          AND batas IS NOT NULL;

    IF geom IS NOT NULL THEN
        UPDATE wilayah
            SET batas = geom
            WHERE key = p_key;
        RAISE NOTICE '% % kini memiliki batas wilayah', p_key, rec.nama;
    ELSE
        RAISE NOTICE '% % tidak ada batas wilayah di bawahnya', p_key, rec.nama;
    END IF;
END $$;


CREATE OR REPLACE FUNCTION gabung(p_tingkat integer)
RETURNS VOID 
LANGUAGE plpgsql
AS $$
-- Cocok digunakan bila proses unduh batas wilayah selesai.
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT key
            FROM wilayah
            WHERE tingkat_id = p_tingkat
            ORDER BY 1
    LOOP
        EXECUTE gabung(rec.key);
    END LOOP;
END $$;



CREATE OR REPLACE FUNCTION gabung_semua(p_key text) 
RETURNS VOID 
LANGUAGE plpgsql AS $$
-- Isi dengan gabungan batas wilayah-wilayah di bawahnya, termasuk cucunya.

-- Cocok saat batas wilayah masih diunduh. Sambil menunggu jalankan dengan
-- p_key = '11' (contoh provinsi) yang otomatis akan mengisi batas kecamatan,
-- kabupaten, dan terakhir provinsinya.
DECLARE
    rec record;
    rec_child record;
    -- geom geometry;
    rec_data record;
BEGIN
    SELECT id, nama, tingkat_id
        INTO rec 
        FROM wilayah
        WHERE key = p_key;

    IF rec.tingkat_id < 3 THEN
        FOR rec_child IN
            SELECT key
                FROM wilayah
                WHERE wilayah_id = rec.id
                ORDER BY key
        LOOP
            EXECUTE gabung_semua(rec_child.key);
        END LOOP;
    END IF;

    SELECT tutup_lubang(ST_UnaryUnion(ST_Collect(ST_MakeValid(batas)))) AS geom,
        sum(data['pria']::int) AS pria,
        sum(data['wanita']::int) AS wanita,
        sum(data['jumlah_penduduk']::int) AS jumlah_penduduk,
        sum(data['jumlah_kk']::int) AS jumlah_kk,
        sum(data['kawin']::int) AS kawin,
        sum(data['belum_kawin']::int) AS belum_kawin,
        sum(data['islam']::int) AS islam, 
        sum(data['kristen']::int) AS kristen, 
        sum(data['katholik']::int) AS katholik, 
        sum(data['hindu']::int) AS hindu,
        sum(data['budha']::int) AS budha,
        sum(data['konghucu']::int) AS konghucu 
        INTO rec_data 
        FROM wilayah
        WHERE wilayah_id = rec.id
          AND batas IS NOT NULL;

    IF rec_data.geom IS NOT NULL THEN
        UPDATE wilayah
            SET batas = rec_data.geom,
                data = jsonb_build_object(
                    'pria', rec_data.pria,
                    'wanita', rec_data.wanita,
                    'jumlah_penduduk', rec_data.jumlah_penduduk,
                    'jumlah_kk', rec_data.jumlah_kk,
                    'kawin', rec_data.kawin,
                    'belum_kawin', rec_data.belum_kawin,
                    'islam', rec_data.islam,
                    'kristen', rec_data.kristen,
                    'katholik', rec_data.katholik,
                    'hindu', rec_data.hindu,
                    'budha', rec_data.budha,
                    'konghucu', rec_data.konghucu)
            WHERE key = p_key;
        RAISE NOTICE '% % kini memiliki batas wilayah', p_key, rec.nama;
    ELSE
        RAISE NOTICE '% % tidak ada batas wilayah di bawahnya', p_key, rec.nama;
    END IF;
END $$;
