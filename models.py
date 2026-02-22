from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    ForeignKey,
    )
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry


Base = declarative_base()


class TingkatWilayah(Base):
    __tablename__ = 'tingkat_wilayah'
    id = Column(Integer, primary_key=True)
    nama = Column(String(32), nullable=False, unique=True)


class JenisWilayah(Base):
    __tablename__ = 'jenis_wilayah'
    id = Column(Integer, primary_key=True)
    nama = Column(String(32), nullable=False, unique=True)
    tingkat_id = Column(
            Integer, ForeignKey(TingkatWilayah.id), nullable=False)


class Wilayah(Base):
    __tablename__ = 'wilayah'
    id = Column(Integer, primary_key=True)
    nama = Column(String(64), nullable=False)
    key = Column(String(16), nullable=False, unique=True)
    wilayah_id = Column(Integer, ForeignKey('wilayah.id'))
    jenis_id = Column(Integer, ForeignKey(JenisWilayah.id))
    tingkat_id = Column(
            Integer, ForeignKey(TingkatWilayah.id), nullable=False)
    nama_lengkap = Column(String(256), nullable=False)
    batas = Column(Geometry('GEOMETRY'))

    def save(self, db_session):
        q = db_session.query(JenisWilayah).filter_by(id=self.jenis_id)
        jenis = q.first()
        self.tingkat_id = jenis.tingkat_id
        if self.wilayah_id:
            q = db_session.query(Wilayah).filter_by(id=self.wilayah_id)
            parent = q.first()
            nama = self.nama
            if self.tingkat_id > 2:  # Kecamatan ke bawah
                nama = ' '.join([jenis.nama, nama])
            self.nama_lengkap = ', '.join([nama, parent.nama_lengkap])
        else:  # Provinsi
            self.nama_lengkap = ' '.join([jenis.nama, self.nama])
        db_session.add(self)
