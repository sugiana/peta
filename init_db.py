import sys
import os
import csv
import re
from configparser import ConfigParser
from argparse import ArgumentParser
from time import time
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
from source_models import Wilayah as SourceWilayah
from common import (
    create_session,
    format_wilayah,
    )


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


# Dipakai oleh script lain
def perbaiki_jenis(db_session, row):
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
        kabupaten_key = row.key[:5]
        q = db_session.query(Wilayah).filter_by(key=kabupaten_key)
        kabupaten = q.first()
        if kabupaten.jenis_id > DEFAULT_KABUPATEN:  # Kota ?
            row.jenis_id = JENIS_KELURAHAN


def perbaiki_nama(row):
    if row.key in NAMA:
        row.nama = NAMA[row.key]
        return
    row.nama = row.nama.replace(KUTIP_TUNGGAL, "'")
    row.nama = row.nama.replace('Kep.', 'Kepulauan')
    karakter_aneh = re.findall(REGEX_NAMA, row.nama)
    if karakter_aneh:
        db_session = registry['target_session']
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


def perbaiki(db_session, row):
    perbaiki_jenis(db_session, row)
    perbaiki_nama(row)


def get_count():
    sql = select(func.count()).select_from(SourceWilayah.__table__)
    with registry['source_engine'].connect() as conn:
        q = conn.execute(sql)
    return q.scalar()


def show_progress(begin_time, count, real_count, no, real_no, info):
    duration = time() - begin_time
    speed = duration / real_no
    remain_row = real_count - real_no
    finish_estimate = remain_row * speed
    estimate = humanize_time(finish_estimate)
    print(f'#{no}/{count} {info["key"]} {info["nama"]} estimate {estimate}')


def get_jenis_id(key):
    t = key.split('.')
    return len(t) * 10


def prepare_new(db_session, key: str):
    jenis_id = get_jenis_id(key)
    if jenis_id == 10:  # Provinsi ?
        parent = None
    else:
        t = key.split('.')
        q = db_session.query(Wilayah).filter_by(key='.'.join(t[:-1]))
        parent = q.first()
    return jenis_id, parent


def restore_from_db(offset=-1):
    target_session = registry['target_session']
    source_session = registry['source_session']
    count = get_count()
    real_count = count - offset - 1
    q_source = source_session.query(SourceWilayah)
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
        jenis_id, parent = prepare_new(target_session, source.kode)
        q = target_session.query(Wilayah).filter_by(key=source.kode)
        target = q.first()
        if not target:
            target = Wilayah(key=source.kode)
        target.nama = nama
        target.jenis_id = jenis_id
        if parent:
            target.wilayah_id = parent.id
        perbaiki(target_session, target)
        log_info = dict(key=source.kode, nama=target.nama)
        with transaction.manager:
            target.save(target_session)
        show_progress(begin_time, count, real_count, no, real_no, log_info)


def get_option(argv):
    offset = 0
    help_offset = f'baris mulai, default {offset}'
    pars = ArgumentParser()
    pars.add_argument('conf')
    pars.add_argument('--offset', type=int, default=offset, help=help_offset)
    return pars.parse_args(argv)


def main(argv=sys.argv[1:]):
    option = get_option(argv)
    conf = ConfigParser()
    conf.read(option.conf)
    cf = dict(conf.items('main'))
    if option.offset > 2:
        offset = option.offset - 2  # Jangan mepet biar keren
    else:
        offset = option.offset
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
    restore_from_db(offset)


if __name__ == '__main__':
    main()
