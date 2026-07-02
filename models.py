import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATA_DIR}/pastebin.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    password_sha = Column(String(64), unique=True, nullable=False, index=True)
    password_plain = Column(String(200), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))]
        if "is_admin" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
        if "password_plain" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN password_plain VARCHAR(200)"))
        conn.commit()


def seed_admin(admin_password: str):
    sha = _sha(admin_password)
    db = SessionLocal()
    try:
        admin = db.query(Account).filter(Account.is_admin == True).first()
        if admin:
            admin.password_sha = sha
        else:
            existing = db.query(Account).filter(Account.password_sha == sha).first()
            if existing:
                existing.is_admin = True
            else:
                db.add(Account(password_sha=sha, is_admin=True))
        db.commit()
    finally:
        db.close()


def _sha(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
