key=$1

if [ -z  "$key" ]; then
    echo "Caranya sh $0 <kode-wilayah>"
    exit 1
fi

geojson_file="kawasan.geojson"
html_file="kawasan.html"

~/env/bin/python db_to_geojson.py live.ini $@ > $geojson_file || exit 1
ls -lh $geojson_file

~/env/bin/python geojson_to_html.py $geojson_file > $html_file || exit 1
ls -lh $html_file
