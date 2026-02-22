import sys
import os
import json
import glob
from configparser import ConfigParser
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement
from shapely.geometry import shape
from models import Base, Wilayah


def wkt_from_geojson(geom):
    """Convert GeoJSON geometry to WKT for PostGIS."""
    if geom is None:
        return None
    shapely_geom = shape(geom)
    return WKTElement(shapely_geom.wkt, srid=4326)


def import_geojson_files(db_session, pattern='*.geojson'):
    files = sorted(glob.glob(pattern))
    if not files:
        pattern = os.path.join('desa', pattern)
        files = sorted(glob.glob(pattern))
    print(f"Found {len(files)} GeoJSON files")

    total_imported = 0

    for filepath in files:
        print(f"Processing: {filepath}")
        with open(filepath, 'r') as f:
            data = json.load(f)

        features = data.get('features', [])
        print(f"  Features: {len(features)}")

        for feature in features:
            props = feature.get('properties', {})
            code = props.get('code')
            name = props.get('name')
            level = props.get('level')
            geometry = feature.get('geometry')

            if not code or not name:
                continue

            # Check if already exists
            existing = db_session.query(Wilayah).filter_by(key=code).first()
            if not existing:
                continue

            # Update only the batas field
            existing.batas = wkt_from_geojson(geometry)
            print(f"  Updated batas: {name}")
            total_imported += 1

        db_session.commit()
        print(f"  Committed. Total imported so far: {total_imported}")

    print(f"\nImport completed. Total: {total_imported} records")


def main():
    conf_file = sys.argv[1] if len(sys.argv) > 1 else 'wilayah.ini'
    geojson_pattern = sys.argv[2] if len(sys.argv) > 2 else '*.geojson'

    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))

    engine = engine_from_config(cf, 'target.')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db_session = factory()

    import_geojson_files(db_session, geojson_pattern)


if __name__ == '__main__':
    main()
