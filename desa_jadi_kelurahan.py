import sys
from configparser import ConfigParser
from zope.sqlalchemy import register
import transaction
from models import Wilayah
from common import create_session
from init_db import (
    create_session,
    perbaiki_jenis,
    KELURAHAN_LIST,
    )


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    register(db_session)
    keys = []
    for key in KELURAHAN_LIST:
        q = db_session.query(Wilayah).filter_by(key=key)
        row = q.first()
        if row.tingkat_id == 3:  # Kecamatan ?
            q = db_session.query(Wilayah).filter_by(wilayah_id=row.id)
            for desa in q:
                keys.append(desa.key)
        else:
            keys.append(key)
    with transaction.manager:
        for key in keys:
            q = db_session.query(Wilayah).filter_by(key=key)
            row = q.first()
            old_name = row.nama_lengkap
            perbaiki_jenis(row)
            row.save(db_session)
            new_name = row.nama_lengkap
            if old_name != new_name:
                print(f'{old_name} -> {new_name}')


if __name__ == '__main__':
    main()
