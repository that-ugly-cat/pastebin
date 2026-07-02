import hashlib
import os
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from models import Account, get_db

SECRET = os.environ.get("SECRET_KEY", "pastebin-dev-secret-change-me")
ALGO = "HS256"


def sha_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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
