TMP=kelurahan.tmp.csv
cat data/desa_jadi_kelurahan.csv | (sed -u 1q; sort) > $TMP
mv $TMP data/kelurahan.csv
