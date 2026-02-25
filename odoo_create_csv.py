import sys
import os
import csv
from configparser import ConfigParser
from pprint import pprint
from models import Wilayah
from common import create_session


MAPPING_FILE = os.path.join('data', 'odoo', 'provinsi.csv')


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    provinsi = dict()
    with open(MAPPING_FILE) as f:
        c = csv.DictReader(f)
        for r in c:
            if r['source_key'] == 'NA':
                continue
            provinsi[r['source_key']] = r['id']
    pprint(provinsi)
    q = db_session.query(Wilayah).filter_by(tingkat_id=2)
    with open('kabupaten.csv', 'w') as f:
        c = csv.writer(f)
        c.writerow(['id', 'name', 'state_id:id'])
        for row in q.order_by(Wilayah.key):
            id = 'kabupaten_' + row.key.replace('.', '_')
            name = row.nama_lengkap.split(',')[0]
            prov_id, kab_id = row.key.split('.')
            state_id = 'base.' + provinsi[prov_id]
            print(id, name, state_id)
            c.writerow([id, name, state_id])
    q = db_session.query(Wilayah).filter_by(tingkat_id=3)
    with open('kecamatan.csv', 'w') as f:
        c = csv.writer(f)
        c.writerow(['id', 'name', 'kabupaten_id:id'])
        for row in q.order_by(Wilayah.key):
            id = 'kecamatan_' + row.key.replace('.', '_')
            name = row.nama_lengkap.split(',')[0]
            kab_id = 'kabupaten_' + '_'.join(row.key.split('.')[:-1])
            print(id, name, kab_id)
            c.writerow([id, name, kab_id])
    q = db_session.query(Wilayah).filter_by(tingkat_id=4)
    nama_lengkap = []
    with open('kelurahan.csv', 'w') as f:
        c = csv.writer(f)
        c.writerow(['id', 'name', 'kecamatan_id:id'])
        for row in q.order_by(Wilayah.key):
            if row.nama_lengkap in nama_lengkap:
                continue
            id = 'kelurahan_' + row.key.replace('.', '_')
            name = row.nama_lengkap.split(',')[0]
            kec_id = 'kecamatan_' + '_'.join(row.key.split('.')[:-1])
            print(id, name, kec_id)
            c.writerow([id, name, kec_id])
            nama_lengkap.append(row.nama_lengkap)


if __name__ == '__main__':
    main()
