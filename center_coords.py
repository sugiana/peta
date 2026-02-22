import json
import sys


def get_center_coordinates(geojson_file):
    """
    Mendapatkan koordinat tengah (centroid) dari file GeoJSON.

    Args:
        geojson_file: Jalur ke file GeoJSON.

    Returns:
        Tuple (latitude, longitude)
    """
    with open(geojson_file, 'r') as f:
        data = json.load(f)

    features = []

    if data.get('type') == 'FeatureCollection':
        features = data.get('features', [])
    elif data.get('type') == 'Feature':
        features = [data]
    elif data.get('type') in ['Polygon', 'MultiPolygon']:
        features = [{'geometry': data}]

    if not features:
        raise Exception("Error: Tidak ada fitur geometri ditemukan.")

    all_lats = []
    all_lons = []

    for feature in features:
        geometry = feature.get('geometry', {})
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates')

        if not coords:
            continue

        if geom_type == 'Polygon':
            # Exterior ring saja (index 0)
            ring = coords[0]
            for lon, lat in ring:
                all_lats.append(lat)
                all_lons.append(lon)

        elif geom_type == 'MultiPolygon':
            # Ambil semua polygon, ambil exterior ring
            for polygon in coords:
                ring = polygon[0]
                for lon, lat in ring:
                    all_lats.append(lat)
                    all_lons.append(lon)

        elif geom_type == 'Point':
            lon, lat = coords
            all_lats.append(lat)
            all_lons.append(lon)

        elif geom_type == 'MultiPoint':
            for lon, lat in coords:
                all_lats.append(lat)
                all_lons.append(lon)

    if not all_lats or not all_lons:
        raise Exception("Error: Tidak ada koordinat valid ditemukan.")

    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    return (center_lat, center_lon)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python center_coords.py <file.geojson>")
        sys.exit(1)

    filename = sys.argv[1]
    lat, lon = get_center_coordinates(filename)
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
