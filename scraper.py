import requests
import json


URL = (
    "https://gis.dukcapil.kemendagri.go.id/arcgis/rest/services/"
    "AGR_VISUAL_KEL_FIX/MapServer/0/query")

HEADERS = {
    "Referer": "https://gis.dukcapil.kemendagri.go.id/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
}


def get_provinsi() -> dict:
    params = {
        "where": "1=1",
        "outFields": "no_prop,nama_prop",
        "f": "json",
        "returnGeometry": "false",
        "orderByFields": "no_prop ASC",
        "returnDistinctValues": "true"
    }
    response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("features"):
        raise Exception("Tidak ditemukan data.")
    d = [(
        str(feature["attributes"]["no_prop"]),
        feature["attributes"]["nama_prop"])
        for feature in data["features"]]
    d = dict(d)
    del d['None']
    return d


def get_kabupaten(kode_prov: int) -> dict:
    where_clause = f"no_prop={kode_prov}"
    params = {
        "where": where_clause,
        "outFields": "no_prop,no_kab,nama_kab",
        "f": "json",
        "returnGeometry": "false",
        "orderByFields": "nama_kab ASC",
        "returnDistinctValues": "true"
    }
    response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("features"):
        raise Exception("Tidak ditemukan data untuk wilayah tersebut.")
    d = [(
        '.'.join([
            str(feature["attributes"]["no_prop"]),
            str(feature["attributes"]["no_kab"]).zfill(2)]),
        feature["attributes"]["nama_kab"])
        for feature in data["features"]]
    return dict(d)


def get_kecamatan(kode_prov: int, kode_kab: int) -> dict:
    where_clause = (
        f"no_prop={kode_prov} AND "
        f"no_kab={kode_kab}")
    params = {
        "where": where_clause,
        "outFields": "no_prop,no_kab,no_kec,nama_kec",
        "f": "json",
        "returnGeometry": "false",
        "orderByFields": "nama_kec ASC",
        "returnDistinctValues": "true"
    }
    response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("features"):
        raise Exception("Tidak ditemukan data untuk wilayah tersebut.")
    d = [(
        '.'.join([
            str(feature["attributes"]["no_prop"]),
            str(feature["attributes"]["no_kab"]).zfill(2),
            str(feature["attributes"]["no_kec"]).zfill(2)]),
        feature["attributes"]["nama_kec"])
        for feature in data["features"]]
    return dict(d)


def get_desa(kode_prov: int, kode_kab: int, kode_kec: int) -> dict:
    where_clause = (
        f"no_prop={kode_prov} AND "
        f"no_kab={kode_kab} AND "
        f"no_kec={kode_kec}")
    params = {
        "where": where_clause,
        "outFields": "no_prop,no_kab,no_kec,no_kel,nama_kel",
        "f": "json",
        "returnGeometry": "false",
        "orderByFields": "nama_kel ASC",
        "returnDistinctValues": "true"
    }
    response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("features"):
        raise Exception("Tidak ditemukan data untuk wilayah tersebut.")
    d = [(
        '.'.join([
            str(feature["attributes"]["no_prop"]),
            str(feature["attributes"]["no_kab"]).zfill(2),
            str(feature["attributes"]["no_kec"]).zfill(2),
            str(feature["attributes"]["no_kel"]).zfill(2)]),
        feature["attributes"]["nama_kel"])
        for feature in data["features"]]
    return dict(d)


def get_info(
        kode_prov: int, kode_kab: int, kode_kec: int, kode_kel: int) -> dict:
    where_clause = (
        f"no_prop={kode_prov} AND "
        f"no_kab={kode_kab} AND "
        f"no_kec={kode_kec} AND "
        f"no_kel={kode_kel}")
    params = {
        "where": where_clause,
        "outFields": "*",
        "f": "json",
        "returnGeometry": "true",
        "outSR": "4326"
    }
    response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if 'features' not in data:
        raise Exception('Tidak ada data')
    f = data['features'][0]
    return dict(
            properties=f['attributes'],
            geometry=f['geometry']['rings'])


def to_geojson(data: dict):
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": data["properties"],
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [data["geometry"]]
                }
            }]
        }


def get_center_coordinates(coordinates: list):
    all_lats = []
    all_lons = []
    ring = coordinates[0]
    for lon, lat in ring:
        all_lats.append(lat)
        all_lons.append(lon)
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    return (center_lat, center_lon)


HTML_TPL = """<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
<div id="map" style="height: 600px;"></div>
<script>
  var map = L.map('map').setView([ {lat}, {lon} ], 7);
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
       attribution:
       '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
   }).addTo(map);
   fetch('{geojson_file}')
       .then(response => response.json())
       .then(data => {
           L.geoJSON(data, {
               style: function(feature) {
                   return { color: 'red', weight: 2 };
               }
           }).addTo(map);
       });
</script>
</body>
</html>
"""


def create_html(key: str, data: dict):
    geojson_file = key + '.geojson'
    geojson = to_geojson(data)
    geojson_str = json.dumps(geojson, indent=2)
    with open(geojson_file, 'w') as f:
        f.write(json_str)
    lat, lon = get_center_coordinates(d['geometry'])
    title = data['properties']['nama_kel']
    html_file = key + '.html'
    html = HTML_TPL.replace('{geojson_file}', geojson_file)
    html = html.replace('{lat}', str(lat))
    html = html.replace('{lon}', str(lon))
    html = html.replace('{title}', title)
    with open(html_file, 'w') as f:
        f.write(html)
    print(f'File {geojson_file} sudah dibuat.')
    print(f'File {html_file} sudah dibuat.')


if __name__ == "__main__":
    import sys

    if sys.argv[1:]:
        key = sys.argv[1]
        t = key.split('.')
        if t[3:]:
            d = get_info(*t)
            if sys.argv[2:]:
                if sys.argv[2] == 'geojson':
                    print(to_geojson(d))
                elif sys.argv[2] == 'html':
                    create_html(key, d)
                sys.exit()
        elif t[2:]:
            d = get_desa(*t)
        elif t[1:]:
            d = get_kecamatan(*t)
        else:
            d = get_kabupaten(*t)
    else:
        d = get_provinsi()
    print(json.dumps(d))
