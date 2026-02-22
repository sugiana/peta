from sqlalchemy import (
    Column,
    String,
    )
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Wilayah(Base):
    __tablename__ = 'wilayah'
    kode = Column(String(13), primary_key=True)
    nama = Column(String(25), nullable=False)
