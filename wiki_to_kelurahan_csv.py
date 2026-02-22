import sys
import json
from configparser import ConfigParser
from sqlalchemy import (
    engine_from_config,
    func,
    )
from sqlalchemy.orm import sessionmaker
from models import Wilayah


def get_kelurahan(json_file: str):
    with open(json_file) as f:
        s = f.read()
    d = json.loads(s)
    r = dict()
    for kec in d:
        if 'Kelurahan' not in kec['detail']:
            continue
        r[kec['kode']] = kec['detail']['Kelurahan']
    return r


def main():
    conf_file = sys.argv[1]
    json_file = 'wiki.json'

    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))

    engine = engine_from_config(cf, 'target.')
    factory = sessionmaker(bind=engine)
    db_session = factory()

    with open(json_file) as f:
        s = f.read()
    d = json.loads(s)
    r = dict()
    for kec in d:
        if 'Kelurahan' not in kec['detail']:
            continue
        key_kec = kec['kode']
        for kelurahan in kec['detail']['Kelurahan']:
            q = db_session.query(Wilayah).filter(
                    Wilayah.key.like(f'{key_kec}.%'),
                    func.similarity(Wilayah.nama, kelurahan) >= 0.3)
            row = q.first()
            if not row:
                kata_pertama = kelurahan.split()[0]
                q = db_session.query(Wilayah).filter(
                        Wilayah.key.like(f'{key_kec}.%'),
                        Wilayah.nama.ilike(f'%{kata_pertama}%'))
                count = 0
                for row in q:
                    count += 1
                if count != 1:
                    sql = ("SELECT key, nama_lengkap FROM wilayah "
                           f"WHERE key LIKE '{key_kec}.%' "
                           f"AND nama ILIKE '%{kata_pertama}%'")
                    raise Exception(
                        f'Kecamatan {key_kec}, kelurahan {kelurahan} '
                        f'tidak ditemukan. Coba cari dengan query:\n{sql};')
            if row.nama_lengkap.find('Kelurahan') == 0:
                continue
            print(','.join([row.key, f'"{row.nama_lengkap}"']))


if __name__ == '__main__':
    main()
