# Deployment and operations

Veil Garden stores complete email addresses that can reveal a user's activity. It listens on `127.0.0.1` by default. Never expose it to a LAN or the public internet without HTTPS, a strong access token, and an exact Host allowlist.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `VEIL_BIND_HOST` | `127.0.0.1` | Listen address |
| `VEIL_PORT` | `8768` | Listen port |
| `VEIL_ACCESS_TOKEN` | generated on loopback | At least 24 characters; required outside loopback |
| `VEIL_ALLOWED_HOSTS` | loopback names added | Comma-separated exact browser hostnames; `*` is forbidden |
| `VEIL_DATA_DIR` | `./data` | SQLite data directory |
| `VEIL_ALLOW_PRIVATE_HTTP` | `0` | Set to `1` only for an isolated Docker/private hop |
| `VEIL_DEMO` | `0` | Reserved `example.invalid` data in an in-memory database |

Generate a token with `veil-garden token`. Never put it in Git, command arguments, URL queries, screenshots, or reverse-proxy access logs. The generated local URL uses a fragment, which the browser removes immediately after reading.

## Local process

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
veil-garden
```

Use `.\.venv\Scripts\Activate.ps1` in Windows PowerShell. Stop with `Ctrl+C`. Data defaults to `data/veil-garden.sqlite3`.

## SSH tunnel

Keep Veil Garden on the server loopback interface and forward it locally:

```bash
ssh -N -L 8768:127.0.0.1:8768 user@example-host
```

Open `http://127.0.0.1:8768/` and enter the server-side token. Keep SSH hosts, users, and keys in your own SSH configuration—not this repository.

## Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

The provided Compose file maps the port to host loopback only, uses a read-only root filesystem, drops Linux capabilities, prevents privilege escalation, and keeps data in a named volume. When an internal reverse proxy reaches the container over a private Docker network, keep `VEIL_ALLOW_PRIVATE_HTTP=1` but do not publish the container port directly.

## systemd and HTTPS

Create a dedicated `veil-garden` system user, place code in `/opt/veil-garden`, and create `/var/lib/veil-garden` with mode `0700`. Install [`deploy/veil-garden.service`](../deploy/veil-garden.service), then create root-only `/etc/veil-garden.env`:

```ini
VEIL_BIND_HOST=127.0.0.1
VEIL_PORT=8768
VEIL_ACCESS_TOKEN=replace-with-a-strong-random-value
VEIL_ALLOWED_HOSTS=garden.example.com
VEIL_DATA_DIR=/var/lib/veil-garden
```

```bash
sudo chmod 0600 /etc/veil-garden.env
sudo systemctl daemon-reload
sudo systemctl enable --now veil-garden
```

Adapt [`deploy/nginx.conf.example`](../deploy/nginx.conf.example) and configure a valid TLS certificate. Preserve the original `Host` and `Origin`; the app does not enable CORS or trust arbitrary forwarded identity headers.

## Health, backup, and updates

`curl --fail http://127.0.0.1:8768/health` is intentionally unauthenticated and returns no private data. Stop the service or use SQLite's online backup tooling before copying the database. Encrypt backups, restrict access, and test restoration.

Before upgrading, keep an encrypted backup and record the current Git tag. After `git pull --ff-only`, reinstall, run the tests, restart the service, and verify both `/health` and the browser workflow. Roll back to a verified tag together with a compatible backup.

