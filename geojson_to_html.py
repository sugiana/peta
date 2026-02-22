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
    html = html.replace('{title}', title)
    html_file = prefix + '.html'
    with open(html_file, 'w') as f:
        f.write(html)
    print(f'File {html_file} sudah dibuat.')


if __name__ == '__main__':
    import sys
    from glob import glob
    if sys.argv[1:]:
        filenames = sys.argv[1:]
    else:
        filenames = glob('*.geojson')
    for filename in filenames:
        to_html(filename)
