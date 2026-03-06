import sys
import os
import csv
import re
import json
from configparser import ConfigParser
from argparse import ArgumentParser
from time import time
from glob import glob
from camelot import read_pdf
from sqlalchemy import (
    func,
    select,
    text,
    )
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
from json_wilayah import get_info


registry = dict()

REGEX_NAMA = r"[^a-zA-Z0-9'\-\ ]"
KUTIP_TUNGGAL = chr(8217)
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


JENIS = dict()
filename = os.path.join('data', 'jenis_wilayah.csv')
with open(filename) as f:
    c = csv.DictReader(f)
    for row in c:
        JENIS[row['nama']] = row['id']


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
    field nama tanpa awalan nama jenis. Contohnya Jakarta tanpa awalan Daerah
    Khusus Ibukota
Kabupaten:
    field nama dengan awalan nama jenis karena ada Kabupaten Bogor dan Kota
    Bogor di Provinsi Jawa Barat
Kecamatan:
    field nama tanpa awalan nama jenis
Kelurahan:
    field nama tanpa awalan nama jenis
'''


def perbaiki_nama(row):
    if row.key in NAMA:
        row.nama = NAMA[row.key]
        return
    row.nama = row.nama.replace(KUTIP_TUNGGAL, "'")
    row.nama = row.nama.replace('Kep.', 'Kepulauan')
    karakter_aneh = re.findall(REGEX_NAMA, row.nama)
    if karakter_aneh:
        db_session = registry['db_session']
        parent_key = '.'.join(row.key.split('.')[:-1])
        q = db_session.query(Wilayah).filter_by(key=parent_key)
        parent = q.first()
        # Agar mudah copas ke mesin pencari
        kecamatan = parent.nama_lengkap.split(',')[0]
        print(f'Key:{row.key}; Cari:wiki {row.nama.title()}, {kecamatan}')
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


def show_progress(begin_time, count, real_count, no, real_no, info):
    duration = time() - begin_time
    speed = duration / real_no
    remain_row = real_count - real_no
    finish_estimate = remain_row * speed
    estimate = humanize_time(finish_estimate)
    print(f'#{no}/{count} {info["key"]} {info["nama"]} estimate {estimate}')


def get_parent(db_session, key: str):
    if len(key) == 2:  # Provinsi
        return
    t = key.split('.')
    parent_key = '.'.join(t[:-1])
    q = db_session.query(Wilayah).filter_by(key=parent_key)
    return q.first()


def mkdir(name: str):
    if not os.path.exists(name):
        os.mkdir(name)


def restore_from_pdf(pdf):
    db_session = registry['db_session']
    mkdir('tmp')
    filename = os.path.join('data', 'pdf.csv')
    with open(filename) as f:
        c = csv.DictReader(f)
        for row in c:
            q = db_session.query(Wilayah).filter_by(key=row['provinsi'])
            if q.first():
                continue
            kode_prov = row['provinsi']
            halaman = row['halaman']
            pattern = os.path.join('tmp', f'{kode_prov}-*.json')
            if not glob(pattern):
                print(f'Pilah kode provinsi {kode_prov} di halaman {halaman}')
                tables = read_pdf(pdf, pages=halaman, flavor='lattice')
                output = os.path.join('tmp', f'{kode_prov}.json')
                tables.export(output, f='json')
            json_files = glob(pattern)
            json_files.sort()
            with transaction.manager:
                for json_file in json_files:
                    print(json_file)
                    with open(json_file) as f:
                        s = f.read()
                    rows = json.loads(s)
                    for row in rows:
                        d = get_info(row)
                        if not d:
                            continue
                        key = d['kode']
                        jenis_id = JENIS[d['jenis']]
                        q = db_session.query(Wilayah).filter_by(key=key)
                        w = q.first()
                        if not w:
                            parent = get_parent(db_session, key)
                            w = Wilayah(key=d['kode'])
                            if parent:
                                w.wilayah_id = parent.id
                        w.nama = d['nama']
                        w.jenis_id = jenis_id
                        perbaiki_nama(w)
                        w.save(db_session)
                        print(f'{w.key} {w.nama_lengkap}')


def get_option(argv):
    pars = ArgumentParser()
    pars.add_argument('conf')
    pars.add_argument('pdf')
    return pars.parse_args(argv)


def main(argv=sys.argv[1:]):
    option = get_option(argv)
    conf = ConfigParser()
    conf.read(option.conf)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    registry['db_session'] = db_session
    register(db_session)
    Base.metadata.create_all(engine)
    with transaction.manager:
        append_csv(TingkatWilayah, 'tingkat_wilayah.csv', ['nama'])
        append_csv(JenisWilayah, 'jenis_wilayah.csv', ['nama'])
    restore_from_pdf(option.pdf)


if __name__ == '__main__':
    main()
