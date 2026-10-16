from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os

from app.config import settings

# Railway provides postgres:// but SQLAlchemy requires postgresql://
db_url = settings.database_url
if db_url.startswith(("postgres://", "postgresql://")):
    db_url = "postgresql+psycopg://" + db_url.split("://", 1)[1]

engine_kwargs = {}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    if os.getenv("VERCEL") == "1":
        engine_kwargs["poolclass"] = NullPool

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
