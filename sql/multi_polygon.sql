SELECT key, nama, ST_NumGeometries(batas)
    FROM wilayah
    WHERE ST_GeometryType(batas) = 'ST_MultiPolygon'
    ORDER BY key
