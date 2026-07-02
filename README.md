<p align="center">
  <b>A minimal, password-only text pastebin.</b><br>
  No usernames, no email, no recovery — the password *is* the account.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: AGPL v3" src="https://img.shields.io/badge/License-AGPLv3-blue.svg"></a>
</p>

---

Pastebin is a self-hosted scratchpad for text snippets. Create an account by picking a
password; open it again from any device with that same password. There's no username and
no recovery flow by design — lose the password, lose the account.

## How it works

- **Create** — choose a password (min 6 characters) to spin up a fresh, empty account.
- **Open** — enter that same password from any device to see your items.
- Internally the password's SHA-256 hash is the account's lookup key; a JWT session cookie
  (30 days, httpOnly) keeps you logged in between visits.

## Features

- **Items**: title + free text, create / edit / delete.
- **Dashboard**: card grid sorted by last-modified.
- **Modal editor**: view and edit modes, `Ctrl+S` to save.
- **Admin panel** (optional, gated by an env var): table of all accounts (created date, last
  activity, item count), current password visible on demand (blurred by default), inline
  password reset per account, read-only view into any account's items.

## Quick start

```bash
git clone https://github.com/that-ugly-cat/pastebin.git
cd pastebin
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000.

## Stack

FastAPI · SQLite (SQLAlchemy) · Jinja2 templates · vanilla JS. No build step.

```
main.py       — routes (landing, create, login, dashboard, API CRUD, admin)
models.py     — Account (password_sha, password_plain, is_admin) + Item
auth.py       — sha256 lookup, JWT, get_current_account, require_admin
templates/    — login, dashboard, admin, admin_items
```

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for production setup (environment variables, Docker, reverse
proxy).

## Tech notes

- Set `SECRET_KEY` in production (there is an insecure default for local dev) — it signs the
  session JWT.
- `ADMIN_PASSWORD` is optional: set it to seed/update the admin account on every startup. Leave
  it unset to run without an admin panel.
- The whole database is a single SQLite file — back up by copying it.

## License

Copyright (C) 2026 Giovanni Spitale. Licensed under AGPL-3.0 — fork it, host it, sell access
to it, but keep it closed-source and you're in violation. No SaaS forks that don't share
back. See [LICENSE](LICENSE).
