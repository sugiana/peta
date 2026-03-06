-- Contoh renggang: 12.71.15.1001,A U R
SELECT key, nama from wilayah where length(nama) - length(replace(nama, ' ', '')) = 1 and length(nama) = 3 order by key;
SELECT key, nama from wilayah where length(nama) - length(replace(nama, ' ', '')) > 1 and length(nama) = 5 order by key;
SELECT key, nama from wilayah where length(nama) - length(replace(nama, ' ', '')) > 2 and length(nama) = 7 order by key;
SELECT key, nama from wilayah where length(nama) - length(replace(nama, ' ', '')) > 3 and length(nama) = 9 order by key;
SELECT key, nama from wilayah where length(nama) - length(replace(nama, ' ', '')) > 4 and length(nama) = 11 order by key;
