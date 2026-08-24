from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from server.utils.config import settings

kwargs = {"connect_args":{"check_same_thread":False}} if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}
engine=create_engine(settings.SQLALCHEMY_DATABASE_URI, **kwargs)
SessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base=declarative_base()

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
