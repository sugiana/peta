import sys
import os
import csv
from configparser import ConfigParser
from time import time
from sqlalchemy import (
    text,
    func,
    )
from sqlalchemy.orm import aliased
from zope.sqlalchemy import register
import transaction
from jaccard_index.jaccard import jaccard_index
from geoalchemy2 import WKTElement
from shapely.geometry import shape
from models import Wilayah
from common import create_session
from dukcapil import (
    get_desa,
    NotFound,
    )
from init_db import (
    create_session,
    NAMA,
    humanize_time,
    )


DUKCAPIL = dict()
filename = os.path.join('data', 'dukcapil.csv')
with open(filename) as f:
    c = csv.DictReader(f)
    for row in c:
        DUKCAPIL[row['key']] = (row['nama'], row['key_menteri'])

Desa = aliased(Wilayah, name='desa')
Kecamatan = aliased(Wilayah, name='kecamatan')


def jangan_renggang(s):
    for ch in s.split():
        if ch[1:]:
            return s
    return s.replace(' ', '')


def perbarui_nama(db_session):
    for key, nama in NAMA.items():
        q = db_session.query(Wilayah).filter_by(key=key)
        row = q.first()
        if not row:
            raise Exception(f'{key} {nama} tidak ada.')
        old_name = row.nama_lengkap
        row.nama = nama
        with transaction.manager:
            row.save(db_session)
            new_name = row.nama_lengkap
            if old_name != new_name:
                print(f'UPDATE {key} {old_name} -> {new_name}')


def get_estimate(begin_time, total_count, current_count):
    duration = time() - begin_time
    speed = duration / current_count
    remain_count = total_count - current_count
    finish_estimate = remain_count * speed
    return humanize_time(finish_estimate)


def wkt_from_geojson(geom):
    """Convert GeoJSON geometry to WKT for PostGIS."""
    shapely_geom = shape(geom)
    return WKTElement(shapely_geom.wkt, srid=4326)


def to_db_geometry(geom):
    d = {"type": "MultiPolygon", "coordinates": [geom]}
    return wkt_from_geojson(d)


def perbarui_data_di_seluruh_tingkatan(engine):
    # Isi field data untuk seluruh kecamatan, kabupaten, dan provinsi.
    # Kecamatan tetap disertakan untuk memastikan
    for tingkat_id in [3, 2, 1]:
        print(
            'Perbarui field batas dan data seluruh wilayah '
            f'tingkat {tingkat_id}')
        sql = text("SELECT gabung(:tingkat_id)")
        with engine.begin() as conn:
            conn.execute(sql, dict(tingkat_id=tingkat_id))


def perbarui_data(db_session):
    def get_filter(q):
        return q.filter(Wilayah.tingkat_id == 3, Wilayah.data == None)

    def get_total_count():
        q = db_session.query(func.count())
        q = get_filter(q)
        return q.scalar()

    def get_query():
        q = db_session.query(Wilayah)
        q = get_filter(q)
        return q.order_by(Wilayah.key)

    def get_key():
        if key_dukcapil in DUKCAPIL:
            _, key = DUKCAPIL[key_dukcapil]
        else:
            key = key_dukcapil
        return key

    def get_filter_dugaan(q):
        kode_kab = key_dukcapil[:5]
        return q.filter(
                Wilayah.key.like(f'{kode_kab}.%'),
                Wilayah.tingkat_id == 4,
                Wilayah.nama.ilike(nama_dukcapil))

    def temukan_desa():
        q = db_session.query(Wilayah).filter_by(key=key)
        desa = q.first()
        if desa:
            return desa
        q = db_session.query(func.count())
        q = get_filter_dugaan(q)
        count = q.scalar()
        if count >= 1:
            q = db_session.query(Wilayah)
            q = get_filter_dugaan(q)
            if count == 1:
                return q.first()
            dugaan_list = []
            for desa in q:
                dugaan = (
                    f'\nMungkin maksudnya {desa.key} {desa.nama_lengkap}.'
                    '\nJadi untuk dukcapil.csv:'
                    f'\n{key_dukcapil},{nama_dukcapil.title()},{desa.key}')
                dugaan_list.append(dugaan)
            dugaan = '\n'.join(dugaan_list)
        else:
            dugaan = ''
        raise NotFound(
            f'{key_dukcapil} Desa {nama_lengkap_dukcapil.title()} '
            f'belum terdaftar.{dugaan}')

    def periksa_kemiripan_nama():
        try:
            similarity = jaccard_index(
                desa.nama.lower(), nama_dukcapil.lower())
        except Exception as e:
            print(f'Key: {key}')
            print(f'  Nama dari Dukcapil: {nama_dukcapil}')
            print(f'  Nama dari Menteri: {desa.nama}')
            print(f'Saran untuk data/dukcapil.csv:')
            print(f'{key},{desa.nama},{key}')
            raise e
        if similarity >= 0.3:
            return True
        persen = int(similarity * 100)
        print(f'Key: {key}')
        print(f'  Nama dari Dukcapil: {nama_lengkap_dukcapil}')
        print(f'  Nama dari Menteri: {desa.nama_lengkap}')
        print(f'  Kemiripan: {persen}%')
        if key in DUKCAPIL:
            print('  Tetap isi data karena sudah terdaftar di dukcapil.csv.')
            return True
        if nama_dukcapil.find('/') < 2:
            return
        for s in nama_dukcapil.split('/'):
            similarity = jaccard_index(desa.nama.lower(), s.lower())
            persen = int(similarity * 100)
            print(f'  {s} {persen}%')
            if similarity >= 0.3:
                print('  Tetap isi karena ada potongan yang sama')
                return True

    def temukan_di_kecamatan_yang_sama():
        kode_kec = key_dukcapil[:8]
        q = db_session.query(Wilayah)
        q = q.filter(Wilayah.key.like(f'{kode_kec}.%'))
        q = q.filter(Wilayah.nama.ilike(nama_dukcapil))
        return q.first()

    def temukan_berdasarkan_nama():
        q = db_session.query(Desa)
        q = q.filter(Desa.wilayah_id == Kecamatan.id)
        q = q.filter(Desa.nama.ilike(nama_dukcapil))
        q = q.filter(Kecamatan.nama.ilike(properties['nama_kec']))
        return q.first()

    total_count = get_total_count()
    q = get_query()
    current_count = no = 0
    begin_time = time()
    for kec in q:
        no += 1
        t = kec.key.split('.')
        kode_kab = '.'.join(t[:2])
        try:
            info = get_desa(*t)  # Unduh statistik desa-desa di kecamatan ini
        except NotFound:
            print(f'Tidak ada kecamatan {kec.key} di Dukcapil')
            continue
        with transaction.manager:
            for key_dukcapil, info in info.items():
                properties = info['properties']
                nama_dukcapil = jangan_renggang(properties['nama_kel'])
                key = get_key()  # kode dari Menteri
                if key_dukcapil in DUKCAPIL:
                    nama_dukcapil, _ = DUKCAPIL[key_dukcapil]
                nama_lengkap_dukcapil = ', '.join([
                    nama_dukcapil, properties['nama_kec'],
                    properties['nama_kab'], properties['nama_prop']])
                desa = temukan_desa()
                if not periksa_kemiripan_nama():
                    desa = temukan_di_kecamatan_yang_sama()
                    if not desa:
                        desa = temukan_berdasarkan_nama()
                        if not desa:
                            raise Exception('Keduanya sangat berbeda')
                desa.data = info['properties']
                if not desa.batas:
                    desa.batas = to_db_geometry(info['geometry'])
                db_session.add(desa)
                print(f'UPDATE {desa.key} {desa.nama_lengkap}')
        # Untuk kecamatan field batas diisi sekarang agar tidak diunduh lagi
        # manakala script terhenti di tengah proses.
        sql = text("SELECT gabung(:key)")
        with db_session.bind.begin() as conn:
            conn.execute(sql, dict(key=kec.key))
        current_count += 1
        estimate = get_estimate(begin_time, total_count, current_count)
        print(f'Perkiraan selesai {estimate}')
    perbarui_data_di_seluruh_tingkatan(db_session.bind)


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    register(db_session)
    perbarui_nama(db_session)
    perbarui_data(db_session)


if __name__ == '__main__':
    main()
