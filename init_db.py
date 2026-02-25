import sys
import os
import csv
import re
from configparser import ConfigParser
from time import time
from zope.sqlalchemy import register
import transaction
from roman import (
    fromRoman,
    InvalidRomanNumeralError,
    )
from models import (
    Base,
    TingkatWilayah,
    JenisWilayah,
    Wilayah,
    )
from common import (
    create_session,
    format_wilayah,
    )
from scraper import (
    get_provinsi,
    get_kabupaten,
    get_kecamatan,
    get_desa,
    )


registry = dict()

REGEX_NAMA = r"[^a-zA-Z0-9'\-\ ]"
VOWELS = "aeiouAEIOU"

JENIS_WILAYAH = {
    'DKI': 11,
    'DAERAH ISTIMEWA': 12,
    'KOTA': 21,
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

NAMA = dict()
filename = os.path.join('data', 'nama.csv')
with open(filename) as f:
    c = csv.DictReader(f)
    for row in c:
        NAMA[row['key']] = row['nama']


def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs)


def get_file(filename):
    base_dir = os.path.split(__file__)[0]
    fullpath = os.path.join(base_dir, 'data', filename)
    return open(fullpath)


def append_csv(table, filename, keys):
    db_session = registry['db_session']
    with get_file(filename) as f:
        reader = csv.DictReader(f)
        filter_ = dict()
        for cf in reader:
            for key in keys:
                val = cf[key] or None
                filter_[key] = val
            q = db_session.query(table).filter_by(**filter_)
            found = q.first()
            if found:
                continue
            row = table()
            for fieldname in cf:
                val = cf[fieldname]
                if not val:
                    continue
                setattr(row, fieldname, val)
            db_session.add(row)


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


def perbaiki_jenis(row):
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
        db_session = registry['db_session']
        kabupaten_key = row.key[:5]
        q = db_session.query(Wilayah).filter_by(key=kabupaten_key)
        kabupaten = q.first()
        if kabupaten.jenis_id > DEFAULT_KABUPATEN:  # Kota ?
            row.jenis_id = JENIS_KELURAHAN


def perbaiki_nama(row):
    if row.key in NAMA:
        row.nama = NAMA[row.key]
        return
    row.nama = row.nama.rstrip('.')
    row.nama = row.nama.replace('KAB.', 'Kabupaten')
    row.nama = row.nama.replace('ADM.', 'Administrasi')
    row.nama = row.nama.replace('KEP.', 'Kepulauan')
    row.nama = row.nama.replace('"', "'")
    karakter_aneh = re.findall(REGEX_NAMA, row.nama)
    if karakter_aneh:
        db_session = registry['db_session']
        parent_key = '.'.join(row.key.split('.')[:-1])
        q = db_session.query(Wilayah).filter_by(key=parent_key)
        parent = q.first()
        # Agar mudah copas ke Google
        kecamatan = parent.nama_lengkap.split(',')[0]
        print(f'Key:{row.key}; Google:{row.nama.title()}, {kecamatan}')
        # Agar mudah copas ke data/nama.csv
        print('Salin ke data/nama.csv untuk diperbaiki:')
        print(f'{row.key},{row.nama.title()}')
        raise Exception(
            f'{row.key},{row.nama.title()}, {parent.nama_lengkap} '
            'ada karakter aneh')
    row.nama = format_wilayah(row.nama)
    kata_list = []
    for kata in row.nama.split():
        if 1 < len(kata) < 5:
            try:
                fromRoman(kata)
                kata_list.append(kata.upper())
                continue
            except InvalidRomanNumeralError:
                pass
        kata_list.append(kata.capitalize())
    row.nama = ' '.join(kata_list)


def show_progress(begin_time, count, real_count, no, real_no, source):
    duration = time() - begin_time
    speed = duration / real_no
    remain_row = real_count - real_no
    finish_estimate = remain_row * speed
    estimate = humanize_time(finish_estimate)
    print(f'#{no}/{count} {source.kode} {source.nama} estimate {estimate}')


def get_jenis_id(key):
    t = key.split('.')
    return len(t) * 10


def save(db_session, key, nama):
    jenis_id = get_jenis_id(key)
    d = dict(key=key, nama=nama, jenis_id=jenis_id)
    row = Wilayah(**d)
    if jenis_id != 10:  # Bukan provinsi ?
        t = key.split('.')
        q = db_session.query(Wilayah).filter_by(key='.'.join(t[:-1]))
        parent = q.first()
        row.wilayah_id = parent.id
    perbaiki_jenis(row)
    perbaiki_nama(row)
    print(key, row.nama)
    row.save(db_session)


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    registry['db_session'] = db_session
    register(db_session)
    Base.metadata.create_all(engine)
    with transaction.manager:
        append_csv(TingkatWilayah, 'tingkat_wilayah.csv', ['nama'])
        append_csv(JenisWilayah, 'jenis_wilayah.csv', ['nama'])
    base_q = db_session.query(Wilayah)
    if not base_q.first():  # Sudah ada provinsi ?
        d_prov = get_provinsi()
        with transaction.manager:
            for key, nama in d_prov.items():
                save(db_session, key, nama)
    q = base_q.filter_by(tingkat_id=1)
    q = q.order_by(Wilayah.key)
    for prov in q:
        q_kab = base_q.filter_by(wilayah_id=prov.id)
        if q_kab.first():  # Sudah ada kabupaten ?
            continue
        d = get_kabupaten(prov.key)
        with transaction.manager:
            for key, nama in d.items():
                save(db_session, key, nama)
    q = base_q.filter_by(tingkat_id=2)
    q = q.order_by(Wilayah.key)
    for kab in q:
        q_kec = base_q.filter_by(wilayah_id=kab.id)
        if q_kec.first():  # Sudah ada kecamatan ?
            continue
        kode_prov, kode_kab = kab.key.split('.')
        d = get_kecamatan(kode_prov, kode_kab)
        with transaction.manager:
            for key, nama in d.items():
                save(db_session, key, nama)
    q = base_q.filter_by(tingkat_id=3)
    q = q.order_by(Wilayah.key)
    for kec in q:
        q_desa = base_q.filter_by(wilayah_id=kec.id)
        if q_desa.first():  # Sudah ada desa ?
            continue
        kode_prov, kode_kab, kode_kec = kec.key.split('.')
        d = get_desa(kode_prov, kode_kab, kode_kec)
        with transaction.manager:
            for key, nama in d.items():
                save(db_session, key, nama)


if __name__ == '__main__':
    main()
