# Deploying Pastebin

Pastebin is a single FastAPI app backed by one SQLite file. No build step, no external
services.

## 1. Configuration (environment variables)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | **yes, in production** | `pastebin-dev-secret-change-me` | signs the session JWT — set a long random value |
| `ADMIN_PASSWORD` | no | unset | if set, seeds/updates the admin account on every startup (enables `/admin`) |

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Local / bare-metal

```bash
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 0.0.0.0 --port 8000
```

The SQLite file is created on first run at `./data/pastebin.db`.

## 3. Docker

```bash
docker compose up -d --build
```

`docker-compose.yml` maps the app to host port `8511` and mounts `./data` for the SQLite
file. Set `SECRET_KEY` and (optionally) `ADMIN_PASSWORD` via a `.env` file or the shell
environment before starting:

```bash
SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
ADMIN_PASSWORD="a-strong-password" \
docker compose up -d --build
```

## 4. Reverse proxy (HTTPS)

Put it behind a proxy that terminates TLS. Example **Caddy**:

```
yourdomain.example {
    reverse_proxy localhost:8511
}
```

## 5. Backups

The entire state (accounts, items) is the one SQLite file under `./data`. Back up by
copying it:

```bash
cp data/pastebin.db backup-$(date +%F).db
```
