import json
import re


RE_PROV = r"^\d{2}$"
RE_KAB = r"^\d{2}\.\d{2}$"
RE_KEC = r"^\d{2}\.\d{2}\.\d{2}$"
RE_DESA = r"^\d{2}\.\d{2}\.\d{2}.\d{4}$"

KOLOM_KEL = '5'
KOLOM_DESA = '6'
TINGKAT = [
    ('Provinsi', RE_PROV, '1'),
    ('Kabupaten', RE_KAB, '1'),
    ('Kecamatan', RE_KEC, '4'),
    ('Desa', RE_DESA, None)]
PROVINSI = [
    'Daerah Khusus Ibukota',
    'Daerah Istimewa',
    'Provinsi']

NAMA = {
    '33.74.16.1007': ('Kelurahan', 'Mangunharjo'),
    '35.08.21.2008': ('Desa', 'Petahunan'),
    '52.72.05.1010': ('Kelurahan', 'Matakando'),
    '94.07.08.2009': ('Desa', 'Sugulubagala'),
    '94.08.05.2005': ('Desa', 'Uwe Onagei'),
    '96.03.24.2004': ('Desa', 'Waiman'),
    }


def get_info(d: dict):
    kode = d['0']
    for tingkat, regex, kolom in TINGKAT:
        if not re.match(regex, kode):
            continue
        if tingkat == 'Desa':
            if kode in NAMA:
                jenis, nama = NAMA[kode]
            else:
                if d[KOLOM_KEL]:
                    jenis = 'Kelurahan'
                    nama = d[KOLOM_KEL]
                else:
                    jenis = 'Desa'
                    print(d)
                    nama = d[KOLOM_DESA]
                nama = ' '.join(nama.split()[1:])
        else:
            nama = d[kolom].replace('\n', ' ')
            if tingkat == 'Kecamatan':
                jenis = tingkat
                nama = ' '.join(nama.split()[1:])
            elif tingkat == 'Kabupaten':
                jenis = nama.split()[0]
                if jenis == 'Kab':
                    jenis = 'Kabupaten'
            else:
                for jenis in PROVINSI:
                    if nama.find(jenis) == 0:
                        p = len(jenis) + 1
                        nama = nama[p:]
                        break
        nama = nama.replace('"', "'")
        return dict(kode=kode, nama=nama, jenis=jenis)


if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    with open(filename) as f:
        s = f.read()
    rows = json.loads(s)
    for row in rows:
        d = get_info(row)
        if d:
            print(d)
