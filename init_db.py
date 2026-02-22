import sys
import os
import csv
from configparser import ConfigParser
from time import time
from sqlalchemy import (
    func,
    select,
    text,
    )
from zope.sqlalchemy import register
import transaction
from models import (
    Base,
    TingkatWilayah,
    JenisWilayah,
    Wilayah,
    )
from source_models import Wilayah as SourceWilayah
from common import create_session


registry = dict()

JENIS_WILAYAH = {
    'Daerah Khusus Ibukota': 11,
    'Daerah Istimewa': 12,
    'Kabupaten': 20,
    'Kota': 21,
    'Kota Administrasi': 21,
    }

DEFAULT_PROVINSI = 10
DEFAULT_KABUPATEN = 20
DEFAULT_DESA = 40
JENIS_KELURAHAN = 41

KELURAHAN_LIST = []
filename = os.path.join('data', 'desa_jadi_kelurahan.csv')
with open(filename) as f:
    c = csv.DictReader(f)
    for row in c:
        KELURAHAN_LIST.append(row['key'])


def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs)


def get_file(filename):
    base_dir = os.path.split(__file__)[0]
    fullpath = os.path.join(base_dir, 'data', filename)
    return open(fullpath)


def append_csv(table, filename, keys):
    target_session = registry['target_session']
    with get_file(filename) as f:
        reader = csv.DictReader(f)
        filter_ = dict()
        for cf in reader:
            for key in keys:
                val = cf[key] or None
                filter_[key] = val
            q = target_session.query(table).filter_by(**filter_)
            found = q.first()
            if found:
                continue
            row = table()
            for fieldname in cf:
                val = cf[fieldname]
                if not val:
                    continue
                setattr(row, fieldname, val)
            target_session.add(row)


'''
Provinsi:
    field nama tanpa awalan nama jenis. Jadi Jakarta saja tanpa awalan Daerah
    Khusus Ibukota
Kabupaten:
    field nama dengan awalan nama jenis karena ada Kabupaten Bogor dan Kota
    Bogor di Provinsi Jawa Barat
Kecamatan:
    field nama tanpa awalan nama jenis
Kelurahan:
    field nama tanpa awalan nama jenis
'''


def repair_row(row):
    row.nama = row.nama.strip()
    if row.jenis_id <= DEFAULT_KABUPATEN:  # Provinsi / Kabupaten / Kota
        for prefix in JENIS_WILAYAH:
            if row.nama.find(prefix) == 0:
                if row.jenis_id == DEFAULT_PROVINSI:
                    p = len(prefix) + 1
                    row.nama = row.nama[p:]
                row.jenis_id = JENIS_WILAYAH[prefix]
                return
    elif row.jenis_id == DEFAULT_DESA:
        for prefix in KELURAHAN_LIST:
            if row.key.find(prefix) == 0:
                row.jenis_id = JENIS_KELURAHAN
                return
        target_session = registry['target_session']
        kabupaten_key = row.key[:5]
        q = target_session.query(Wilayah).filter_by(key=kabupaten_key)
        kabupaten = q.first()
        if kabupaten.jenis_id > DEFAULT_KABUPATEN:  # Kota ?
            row.jenis_id = JENIS_KELURAHAN


def get_count():
    sql = select(func.count()).select_from(SourceWilayah.__table__)
    with registry['source_engine'].connect() as conn:
        q = conn.execute(sql)
    return q.scalar()


def show_progress(begin_time, count, real_count, no, real_no, source):
    duration = time() - begin_time
    speed = duration / real_no
    remain_row = real_count - real_no
    finish_estimate = remain_row * speed
    estimate = humanize_time(finish_estimate)
    print(f'#{no}/{count} {source.kode} {source.nama} estimate {estimate}')


def restore_from_source():
    target_session = registry['target_session']
    source_session = registry['source_session']
    count = get_count()
    q_source = source_session.query(SourceWilayah)
    if sys.argv[2:]:
        offset = int(sys.argv[2]) - 2
        real_count = count - offset - 1
    else:
        offset = -1
        real_count = count
    real_no = 0
    begin_time = time()
    while True:
        offset += 1
        source = q_source.order_by(SourceWilayah.kode).offset(offset).first()
        if not source:
            break
        real_no += 1
        no = offset + 1
        nama = source.nama
        t = source.kode.split('.')
        jenis_id = len(t) * 10
        if jenis_id == 10:
            parent = None
        else:
            q = target_session.query(Wilayah).filter_by(key='.'.join(t[:-1]))
            parent = q.first()
        q = target_session.query(Wilayah).filter_by(key=source.kode)
        row = q.first()
        with transaction.manager:
            if not row:
                row = Wilayah(key=source.kode)
            row.nama = nama
            row.jenis_id = jenis_id
            if parent:
                row.wilayah_id = parent.id
            repair_row(row)
            row.save(target_session)
        show_progress(begin_time, count, real_count, no, real_no, source)


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    target_engine, target_session = create_session(cf, 'target.')
    source_engine, source_session = create_session(cf, 'source.')
    registry['source_engine'] = source_engine
    registry['target_session'] = target_session
    registry['source_session'] = source_session
    register(target_session)
    Base.metadata.create_all(target_engine)
    with transaction.manager:
        append_csv(TingkatWilayah, 'tingkat_wilayah.csv', ['nama'])
        append_csv(JenisWilayah, 'jenis_wilayah.csv', ['nama'])
    restore_from_source()


if __name__ == '__main__':
    main()
