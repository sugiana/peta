SELECT st_y(ST_Centroid(batas)) AS lat, st_x(st_centroid(batas)) AS lng, nama
    FROM wilayah
    WHERE key = '32.76.01.1010'
