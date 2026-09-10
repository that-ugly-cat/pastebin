import asyncio
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler as _default_http_exc
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import (create_token, get_current_account, lookup_index, make_verifier,
                  require_admin, sha_password, verify_password)
from models import Account, Item, get_db, init_db, opaque_legacy_index, seed_admin

app = FastAPI(title="Pastebin")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

init_db()
if _admin_pw := os.environ.get("ADMIN_PASSWORD"):
    seed_admin(_admin_pw)


@app.exception_handler(HTTPException)
async def redirect_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 302 and exc.headers and "Location" in exc.headers:
        resp = RedirectResponse(exc.headers["Location"], status_code=302)
        if exc.headers["Location"] == "/":
            resp.delete_cookie("access_token")
        return resp
    return await _default_http_exc(request, exc)


# ── Guess throttling ──────────────────────────────────────────────────────────
#
# Guessing is a working way in here, not merely a way to take over one account:
# the password *is* the identity, so there is no username to be wrong about and
# every guess is a guess against every account at once. The shape is the one the
# ArguMap class codes use — a delay first, a refusal only past a much higher
# count — because a lecture hall is one NATed address and a hard block after a
# few dozen collective typos would lock out the people who typed correctly.

_FAILURES: dict[str, list[float]] = defaultdict(list)
_SOFT_LIMIT, _HARD_LIMIT, _WINDOW = 8, 40, 60.0


def _client_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _recent_failures(key: str) -> int:
    now = time.monotonic()
    hits = [t for t in _FAILURES[key] if now - t < _WINDOW]
    _FAILURES[key] = hits
    return len(hits)


async def _throttle(request: Request) -> bool:
    """True when the caller should be refused outright."""
    n = _recent_failures(_client_key(request))
    if n >= _HARD_LIMIT:
        return True
    if n >= _SOFT_LIMIT:
        await asyncio.sleep(1.0)
    return False


def _record_failure(request: Request) -> None:
    _FAILURES[_client_key(request)].append(time.monotonic())


# ── Landing ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error_login": "", "error_create": ""})


@app.post("/create")
async def create_account(
    request: Request,
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(get_db),
):
    ctx = {"error_login": "", "error_create": ""}
    if await _throttle(request):
        ctx["error_create"] = "Too many attempts. Wait a minute and try again."
        return templates.TemplateResponse(request, "login.html", ctx, status_code=429)
    if password != password2:
        ctx["error_create"] = "Passwords do not match."
        return templates.TemplateResponse(request, "login.html", ctx, status_code=400)
    if len(password) < 6:
        ctx["error_create"] = "Password must be at least 6 characters."
        return templates.TemplateResponse(request, "login.html", ctx, status_code=400)
    # Both indices, because an account that has not logged in since the upgrade
    # is still findable only by the legacy one — and two accounts sharing a
    # password would be indistinguishable at login.
    taken = db.query(Account).filter(
        (Account.pw_lookup == lookup_index(password)) |
        (Account.password_sha == sha_password(password))
    ).first()
    if taken:
        _record_failure(request)
        ctx["error_create"] = "Password already taken. Choose another, or log in below."
        return templates.TemplateResponse(request, "login.html", ctx, status_code=400)
    account = Account(password_sha=opaque_legacy_index(),
                      pw_lookup=lookup_index(password),
                      pw_verify=make_verifier(password))
    db.add(account)
    db.commit()
    db.refresh(account)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("access_token", create_token(account.id), httponly=True, samesite="lax", max_age=86400 * 30)
    return resp


@app.post("/login")
async def login(
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if await _throttle(request):
        ctx = {"error_login": "Too many attempts. Wait a minute and try again.", "error_create": ""}
        return templates.TemplateResponse(request, "login.html", ctx, status_code=429)

    account = db.query(Account).filter(Account.pw_lookup == lookup_index(password)).first()
    if account and not verify_password(password, account.pw_verify):
        account = None  # index hit without the verifier agreeing: not this password
    if not account:
        # Not upgraded yet: found by the legacy index, and upgraded here, once,
        # from the password the person just typed. Nobody is asked to reset
        # anything and nobody notices.
        legacy = db.query(Account).filter(
            Account.password_sha == sha_password(password)).first()
        if legacy:
            legacy.pw_lookup = lookup_index(password)
            legacy.pw_verify = make_verifier(password)
            legacy.password_sha = opaque_legacy_index()
            db.commit()
            account = legacy
    if not account:
        _record_failure(request)
        ctx = {"error_login": "Incorrect password.", "error_create": ""}
        return templates.TemplateResponse(request, "login.html", ctx, status_code=401)
    resp = RedirectResponse("/admin" if account.is_admin else "/dashboard", status_code=302)
    resp.set_cookie("access_token", create_token(account.id), httponly=True, samesite="lax", max_age=86400 * 30)
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("access_token")
    return resp


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    if account.is_admin:
        return RedirectResponse("/admin", status_code=302)
    rows = db.query(Item).filter(Item.account_id == account.id).order_by(Item.updated_at.desc()).all()
    items = [_item_ctx(r) for r in rows]
    return templates.TemplateResponse(request, "dashboard.html", {"items": items})


# ── Items API ─────────────────────────────────────────────────────────────────

@app.post("/api/items")
async def create_item(
    request: Request,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    body = await request.json()
    title = (body.get("title") or "").strip()
    text = (body.get("text") or "").strip()
    if not title:
        raise HTTPException(400, "Title required")
    item = Item(account_id=account.id, title=title, text=text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_json(item)


@app.put("/api/items/{item_id}")
async def update_item(
    item_id: int,
    request: Request,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id, Item.account_id == account.id).first()
    if not item:
        raise HTTPException(404, "Not found")
    body = await request.json()
    title = (body.get("title") or "").strip()
    text = (body.get("text") or "").strip()
    if not title:
        raise HTTPException(400, "Title required")
    item.title = title
    item.text = text
    item.updated_at = datetime.utcnow()
    db.commit()
    return _item_json(item)


@app.delete("/api/items/{item_id}")
async def delete_item(
    item_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id, Item.account_id == account.id).first()
    if not item:
        raise HTTPException(404, "Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    admin: Account = Depends(require_admin),
    db: Session = Depends(get_db),
    reset: int = 0,
    error: str = "",
):
    accounts = db.query(Account).filter(Account.is_admin == False).order_by(Account.created_at).all()
    rows = []
    for a in accounts:
        count = db.query(Item).filter(Item.account_id == a.id).count()
        last = db.query(Item).filter(Item.account_id == a.id).order_by(Item.updated_at.desc()).first()
        rows.append({
            "id": a.id,
            "created_at": a.created_at.strftime("%b %d, %Y"),
            "item_count": count,
            "last_activity": last.updated_at.strftime("%b %d, %Y") if last else "—",
        })
    return templates.TemplateResponse(request, "admin.html", {
        "rows": rows,
        "reset_id": reset,
        "error": error,
    })


@app.post("/admin/accounts/{account_id}/reset")
async def admin_reset_password(
    account_id: int,
    new_password: str = Form(...),
    admin: Account = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if len(new_password) < 6:
        return RedirectResponse("/admin?error=Password+must+be+at+least+6+characters", status_code=302)
    account = db.query(Account).filter(Account.id == account_id, Account.is_admin == False).first()
    if not account:
        return RedirectResponse("/admin", status_code=302)
    collision = db.query(Account).filter(
        (Account.pw_lookup == lookup_index(new_password)) |
        (Account.password_sha == sha_password(new_password)),
        Account.id != account_id,
    ).first()
    if collision:
        return RedirectResponse("/admin?error=Password+already+in+use+by+another+account", status_code=302)
    account.pw_lookup = lookup_index(new_password)
    account.pw_verify = make_verifier(new_password)
    account.password_sha = opaque_legacy_index()
    db.commit()
    return RedirectResponse(f"/admin?reset={account_id}", status_code=302)


@app.get("/admin/accounts/{account_id}", response_class=HTMLResponse)
async def admin_view_account(
    account_id: int,
    request: Request,
    admin: Account = Depends(require_admin),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id, Account.is_admin == False).first()
    if not account:
        raise HTTPException(404)
    rows = db.query(Item).filter(Item.account_id == account_id).order_by(Item.updated_at.desc()).all()
    items = [_item_ctx(r) for r in rows]
    return templates.TemplateResponse(request, "admin_items.html", {
        "account_id": account_id,
        "items": items,
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item_ctx(r: Item) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "text": r.text,
        "preview": (r.text.replace("\n", " ")[:120] + "…" if len(r.text) > 120 else r.text.replace("\n", " ")) if r.text else "",
        "updated_at": r.updated_at.strftime("%b %d, %Y"),
    }


def _item_json(item: Item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "text": item.text,
        "updated_at": item.updated_at.strftime("%b %d, %Y"),
    }
