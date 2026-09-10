import os
import secrets
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
    # The legacy index: a bare SHA-256 of the password. Still unique and NOT
    # NULL because the column was born that way, but no longer how an account is
    # found — see auth.lookup_index. A row that has been upgraded carries an
    # opaque value here that no password can hash to.
    password_sha = Column(String(64), unique=True, nullable=False, index=True)
    # HMAC of the password, keyed with a secret outside the database. This is
    # what turns a typed password into a row.
    pw_lookup = Column(String(64), unique=True, nullable=True, index=True)
    # bcrypt. This is what decides whether the password is right.
    pw_verify = Column(String(200), nullable=True)
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


def opaque_legacy_index() -> str:
    """A value for the legacy column that no SHA-256 of a password can equal.

    The column is unique and NOT NULL, so an upgraded row still needs something
    in it; a 64-character hex string would risk colliding with a real hash, and
    a prefix cannot be produced by hashlib.
    """
    return "upgraded:" + secrets.token_hex(24)


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))]
        if "is_admin" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
        if "password_plain" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN password_plain VARCHAR(200)"))
        if "pw_lookup" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN pw_lookup VARCHAR(64)"))
        if "pw_verify" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN pw_verify VARCHAR(200)"))
        conn.commit()
    _migrate_passwords()


def _migrate_passwords():
    """Derive the new columns from the plaintext, then destroy the plaintext.

    The password column used to hold the password as typed, and the admin page
    displayed it. Nobody has to change their password for this: every row that
    still carries the plaintext is converted here, once, and emptied. A row
    without plaintext — the seeded admin, or an account created before that
    column existed — keeps its legacy index and is upgraded the next time
    somebody logs into it (see main.login).
    """
    from auth import lookup_index, make_verifier  # imported here: auth imports models

    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))]
        if "password_plain" not in cols:
            return
        rows = conn.execute(text(
            "SELECT id, password_plain FROM accounts "
            "WHERE password_plain IS NOT NULL AND password_plain != ''"
        )).fetchall()
        for row_id, plain in rows:
            conn.execute(
                text("UPDATE accounts SET pw_lookup = :lk, pw_verify = :vf, "
                     "password_sha = :sha, password_plain = NULL WHERE id = :id"),
                {"lk": lookup_index(plain), "vf": make_verifier(plain),
                 "sha": opaque_legacy_index(), "id": row_id},
            )
        # Nothing reads the column any more; empty whatever is left in it.
        conn.execute(text("UPDATE accounts SET password_plain = NULL "
                          "WHERE password_plain IS NOT NULL"))
        conn.commit()
        if rows:
            print(f"[pastebin] migrated {len(rows)} account(s) off plaintext passwords")


def seed_admin(admin_password: str):
    from auth import lookup_index, make_verifier

    db = SessionLocal()
    try:
        lk = lookup_index(admin_password)
        admin = db.query(Account).filter(Account.is_admin == True).first()
        if admin:
            admin.pw_lookup = lk
            admin.pw_verify = make_verifier(admin_password)
            if not str(admin.password_sha or "").startswith("upgraded:"):
                admin.password_sha = opaque_legacy_index()
        else:
            existing = db.query(Account).filter(Account.pw_lookup == lk).first()
            if existing:
                existing.is_admin = True
            else:
                db.add(Account(password_sha=opaque_legacy_index(), pw_lookup=lk,
                               pw_verify=make_verifier(admin_password), is_admin=True))
        db.commit()
    finally:
        db.close()
