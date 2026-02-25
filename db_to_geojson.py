import json
import sys
from configparser import ConfigParser
from sqlalchemy import engine_from_config, func
from sqlalchemy.orm import sessionmaker
from models import Wilayah


def export_geojson(db_session, keys: list):
    q = db_session.query(
        Wilayah,
        func.ST_AsGeoJSON(Wilayah.batas).label('geojson')
    ).filter(Wilayah.key.in_(keys))

    features = []
    for w, geojson_str in q:
        if geojson_str is None:
            continue
        geojson_geom = json.loads(geojson_str)
        feature = {
            "type": "Feature",
            "properties": {
                "id": w.id,
                "nama": w.nama,
                "key": w.key,
                "nama_lengkap": w.nama_lengkap,
            },
            "geometry": geojson_geom,
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    print(json.dumps(geojson, indent=2))


def main():
    conf_file = sys.argv[1]
    keys = sys.argv[2:]

    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))

    engine = engine_from_config(cf, 'sqlalchemy.')
    factory = sessionmaker(bind=engine)
    db_session = factory()

    export_geojson(db_session, keys)


if __name__ == '__main__':
    main()
