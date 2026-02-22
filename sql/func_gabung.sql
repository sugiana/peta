CREATE OR REPLACE FUNCTION tutup_lubang(geom geometry)
RETURNS geometry
LANGUAGE plpgsql
AS $$
BEGIN
    -- Jika MultiPolygon, kita harus memproses setiap Polygon di dalamnya
    RETURN ST_Collect(ST_MakePolygon(ST_ExteriorRing(dumped.geom)))
    FROM ST_Dump(geom) AS dumped;
END;
$$;

CREATE OR REPLACE FUNCTION gabung(p_key text) 
RETURNS VOID 
LANGUAGE plpgsql AS $$
DECLARE
    rec_parent record;
    geom geometry;
BEGIN
    SELECT id, nama
        INTO rec_parent 
        FROM wilayah
        WHERE key = p_key;

    RAISE NOTICE '% %', p_key, rec_parent.nama;

    SELECT tutup_lubang(ST_UnaryUnion(ST_Collect(ST_MakeValid(batas))))
        INTO geom
        FROM wilayah
        WHERE wilayah_id = rec_parent.id;

    UPDATE wilayah
        SET batas = geom
        WHERE key = p_key;
END $$;

CREATE OR REPLACE FUNCTION gabung(p_tingkat integer)
RETURNS VOID 
LANGUAGE plpgsql AS $$
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
