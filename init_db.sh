conf=$1
proxy=$2

if [ -z "$conf" ]; then
    echo "Sertakan file konfigurasi."
    exit 1
fi

if ~/env/bin/python init_db.py $conf; then 
    exit 0
fi

info=$(~/env/bin/python init_db.py $conf | grep "Key:")
if [ -z "$info" ]; then
    exit 0
fi
key=$(echo "$info" | awk -F";" '{print $1}' | awk -F":" '{print $2}')
cari=$(echo "$info" | awk -F";" '{print $2}' | awk -F":" '{print $2}')
if [ -z "$proxy" ]; then
    ~/env/bin/python scrape_google.py "$cari" > nama.json || exit 1
else
    ~/env/bin/python scrape_duckduckgo.py "$cari" $proxy > nama.json || exit 1
fi
nama=$(cat nama.json | jq -r .title | awk -F"," '{print $1}')
echo $key,$nama >> data/nama.csv
tail -n 2 data/nama.csv
