import os
from center_coords import get_center_coordinates


def to_html(filename):
    short_file = os.path.split(filename)[-1]
    prefix = os.path.splitext(short_file)[0]
    title = prefix.replace('_', ' ').title()
    lat, lon = get_center_coordinates(filename)
    with open('peta.html.tpl') as f:
        html = f.read()
    geojson_file = prefix + '.geojson'
    html = html.replace('{geojson_file}', geojson_file)
    html = html.replace('{lat}', str(lat))
    html = html.replace('{lon}', str(lon))
    return html.replace('{title}', title)


if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    print(to_html(filename))
