FILENAME=$1

if [ -z "$FILENAME" ]; then
    echo "Caranya sh $0 <file-csv>"
    exit 1
fi

TMP=tmp.csv
cat $FILENAME | (sed -u 1q; sort) > $TMP
mv $TMP $FILENAME
