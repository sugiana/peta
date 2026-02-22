from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker


def create_session(d: dict, prefix: str):
    engine = engine_from_config(d, prefix)
    factory = sessionmaker(bind=engine)
    return engine, factory()
