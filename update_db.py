import sys
import os
import json
import glob
from time import time
from configparser import ConfigParser
from sqlalchemy import (
    engine_from_config,
    func,
    or_
    )
from sqlalchemy.orm import sessionmaker
from models import (
    Base,
    Wilayah,
    )
from scraper import get_info
from init_db import to_db_geometry


def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs)


def get_estimate(total_count: int, current_count: int, begin_time) -> float:
    duration = time() - begin_time
    speed = duration / current_count
    remain_count = total_count - current_count
    return remain_count * speed


def main(argv=sys.argv[1:]):
    def query_filter(q):
        return q.filter(
            Wilayah.tingkat_id == 4, or_(
                Wilayah.batas == None,
                Wilayah.data == None))

    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))

    engine = engine_from_config(cf, 'sqlalchemy.')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db_session = factory()

    q = db_session.query(func.count())
    q = query_filter(q)
    total_count = q.scalar()
    q = db_session.query(Wilayah)
    q = query_filter(q)
    q = q.order_by(Wilayah.key)
    current_count = 0
    begin_time = time()
    for desa in q:
        current_count += 1
        kode_prov, kode_kab, kode_kec, kode_desa = desa.key.split('.')
        info = get_info(kode_prov, kode_kab, kode_kec, kode_desa)
        desa.batas = to_db_geometry(info['geometry'])
        desa.data = info['properties']
        db_session.add(desa)
        db_session.commit()
        estimate = get_estimate(total_count, current_count, begin_time)
        s = humanize_time(estimate)
        s = f'{current_count}/{total_count} perkiraan {s}'
        print(desa.key, desa.nama_lengkap, s)


if __name__ == '__main__':
    main()
