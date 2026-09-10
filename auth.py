import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from models import Account, get_db

SECRET = os.environ.get("SECRET_KEY", "pastebin-dev-secret-change-me")
ALGO = "HS256"

# The password is the account here, so the database needs a deterministic way to
# find a row from a typed password. A bare SHA-256 does that and nothing else:
# it is fast, unsalted and identical on every installation, so a stolen database
# is a dictionary attack that takes minutes. The lookup index is now an HMAC
# keyed with a secret that lives in the environment and not in the file, which
# leaves a thief with the file alone unable to test a single guess offline.
#
# PASTEBIN_PEPPER must not change once accounts exist: it is the only way back
# from a typed password to its row, and there is no plaintext left to rebuild it
# from. Falls back to SECRET_KEY so an existing deployment keeps working.
PEPPER = os.environ.get("PASTEBIN_PEPPER") or SECRET


def lookup_index(password: str) -> str:
    """The deterministic index used to find the account. Not a credential check."""
    return hmac.new(PEPPER.encode(), password.encode(), hashlib.sha256).hexdigest()


def sha_password(password: str) -> str:
    """The pre-2026 index. Kept only to recognise a row that has not been
    upgraded yet — an account created before the pepper existed still has to be
    able to log in, once, and it is upgraded in place when it does."""
    return hashlib.sha256(password.encode()).hexdigest()


def _bcrypt_input(password: str) -> bytes:
    # bcrypt silently truncates at 72 bytes, so hash first: a long passphrase
    # keeps all of its entropy instead of the first 72 bytes of it.
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def make_verifier(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt()).decode()


def verify_password(password: str, verifier: str | None) -> bool:
    if not verifier:
        return False
    try:
        return bcrypt.checkpw(_bcrypt_input(password), verifier.encode())
    except ValueError:
        return False


def create_token(account_id: int) -> str:
    payload = {"sub": str(account_id), "exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def get_current_account(request: Request, db: Session = Depends(get_db)) -> Account:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(302, headers={"Location": "/"})
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        account_id = int(payload["sub"])
    except Exception:
        raise HTTPException(302, headers={"Location": "/"})
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(302, headers={"Location": "/"})
    return account


def require_admin(account: Account = Depends(get_current_account)) -> Account:
    if not account.is_admin:
        raise HTTPException(403, "Not authorized")
    return account
