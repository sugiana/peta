import sys
from configparser import ConfigParser
import json
from sqlalchemy import (
    engine_from_config,
    text,
    )


def str_sql(s):
    return s.replace("'", "''") if s is not None else 'NULL'


conf_file = sys.argv[1]
conf = ConfigParser()
conf.read(conf_file)
cf = dict(conf.items('main'))

engine = engine_from_config(cf, 'sqlalchemy.')

sql = ("SELECT key, nama, tingkat_id, "
       "CASE WHEN tingkat_id = 4 THEN data ELSE NULL END AS data "
       "FROM wilayah ORDER BY key")
sql = text(sql)

with engine.connect() as conn:
    result = conn.execute(sql)
    rows = result.fetchall()
    print("CREATE TABLE IF NOT EXISTS wilayah (")
    print("  kode VARCHAR(50) PRIMARY KEY,")
    print("  nama VARCHAR(255) NOT NULL,")
    print("  tingkat_id INT NOT NULL,")
    print("  data JSON")
    print(");")
    for row in rows:
        key, nama, tingkat_id, data = row
        # Escape single quotes for SQL
        key_escaped = str_sql(key)
        nama_escaped = str_sql(nama)
        # Handle JSON data - escape double quotes with backslash for MySQL JSON
        if data is not None:
            d = dict()
            for k, v in data.items():
                if isinstance(v, str):
                    v = str_sql(v)
                d[k] = v
            data_str = json.dumps(d, ensure_ascii=False)
            # Escape backslashes first, then double quotes for MySQL
            data_escaped = data_str.replace('\\', '\\\\')
            data_sql = f"'{data_escaped}'"
        else:
            data_sql = 'NULL'
        # Quote key (now 'kode') as VARCHAR
        key_sql = f"'{key_escaped}'"
        if isinstance(nama, (int, float)):
            nama_sql = str(nama)
        else:
            nama_sql = f"'{nama_escaped}'"
        print(
            ("INSERT INTO wilayah (kode, nama, tingkat_id, data) "
             f"VALUES ({key_sql}, {nama_sql}, {tingkat_id}, {data_sql});"))
