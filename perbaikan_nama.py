import sys
from configparser import ConfigParser
from zope.sqlalchemy import register
import transaction
from models import Wilayah
from common import create_session
from init_db import (
    create_session,
    NAMA,
    )


def main(argv=sys.argv[1:]):
    conf_file = argv[0]
    conf = ConfigParser()
    conf.read(conf_file)
    cf = dict(conf.items('main'))
    engine, db_session = create_session(cf, 'sqlalchemy.')
    register(db_session)
    keys = []
    for key, nama in NAMA.items():
        print([key])
        q = db_session.query(Wilayah).filter_by(key=key)
        row = q.first()
        old_name = row.nama_lengkap
        row.nama = nama
        with transaction.manager:
            row.save(db_session)
            new_name = row.nama_lengkap
            if old_name != new_name:
                print(f'{old_name} -> {new_name}')


if __name__ == '__main__':
    main()
