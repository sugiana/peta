proxy=$1

if ~/env/bin/python init_db.py live.ini; then 
    exit 0
fi

info=$(~/env/bin/python init_db.py live.ini | grep "Key:")
if [ -z "$info" ]; then
    exit 0
fi
key=$(echo "$info" | awk -F";" '{print $1}' | awk -F":" '{print $2}')
cari=$(echo "$info" | awk -F";" '{print $2}' | awk -F":" '{print $2}')
#~/env/bin/python scrape_google.py "$cari" > nama.json || exit 1
~/env/bin/python scrape_duckduckgo.py "$cari" $proxy > nama.json || exit 1
nama=$(cat nama.json | jq -r .title | awk -F"," '{print $1}')
echo $key,$nama >> data/nama.csv
tail -n 2 data/nama.csv
