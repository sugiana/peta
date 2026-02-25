TMP=nama.tmp.csv
cat data/nama.csv | (sed -u 1q; sort) > $TMP
mv $TMP data/nama.csv
