from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:  # serverless: no long-lived pools; use a pooled (pgbouncer) URL from your provider
    engine = create_engine(DATABASE_URL, poolclass=NullPool, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
