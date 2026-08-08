from __future__ import annotations

import csv
import io
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .config import AppConfig
from .security import (
    SlidingWindowLimiter,
    bearer_matches,
    clean_text,
    host_allowed,
    mask_email,
    same_origin,
)
from .store import AliasStore

MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
OFFICIAL_GUIDE = "https://support.apple.com/guide/icloud/create-and-edit-addresses-mm1a876f7aed/icloud"
STATIC_NAMES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
    "/favicon.svg": "favicon.svg",
    "/favicon.ico": "favicon.ico",
    "/apple-touch-icon.png": "apple-touch-icon.png",
}
STATIC_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml; charset=utf-8",
}


class _GardenHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: VeilGardenServer) -> None:
        self.app = app
        super().__init__(address, GardenHandler)


class VeilGardenServer:
    def __init__(self, config: AppConfig, *, store: AliasStore | None = None) -> None:
        self.config = config
        self.store = store or AliasStore(
            ":memory:" if config.demo else config.data_dir / "veil-garden.sqlite3"
        )
        if config.demo:
            self.store.seed_demo()
        self.read_limiter = SlidingWindowLimiter(limit=240, window_seconds=60)
        self.write_limiter = SlidingWindowLimiter(limit=60, window_seconds=60)
        self.static_root = Path(str(files("veil_garden").joinpath("static")))
        self.httpd: _GardenHTTPServer | None = None

    def serve_forever(self) -> None:
        self.httpd = _GardenHTTPServer((self.config.bind_host, self.config.port), self)
        try:
            self.httpd.serve_forever(poll_interval=0.3)
        finally:
            self.httpd.server_close()
            self.store.close()

    def shutdown(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()


class GardenHandler(BaseHTTPRequestHandler):
    server_version = "VeilGarden"
    sys_version = ""

    @property
    def app(self) -> VeilGardenServer:
        return self.server.app  # type: ignore[attr-defined, no-any-return]

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _security_headers(self, *, cache: str = "no-store") -> None:
        self.send_header("Cache-Control", cache)
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        cache: str = "no-store",
        disposition: str | None = None,
    ) -> None:
        if len(body) > MAX_RESPONSE_BYTES:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "response too large"})
            return
        self.send_response(status)
        self._security_headers(cache=cache)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any] | list[Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._send_json(status, {"ok": False, "error": clean_text(message, limit=160)})

    def _host_ok(self) -> bool:
        if host_allowed(self.headers.get("Host"), self.app.config.allowed_hosts):
            return True
        self._error(HTTPStatus.BAD_REQUEST, "invalid host")
        return False

    def _auth_ok(self) -> bool:
        if bearer_matches(self.headers.get("Authorization"), self.app.config.access_token):
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self._security_headers()
        self.send_header("WWW-Authenticate", "Bearer")
        body = b'{"ok":false,"error":"access token required"}'
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return False

    def _write_guard(self) -> bool:
        fetch_site = (self.headers.get("Sec-Fetch-Site") or "").lower()
        if fetch_site not in {"", "none", "same-origin"}:
            self._error(HTTPStatus.FORBIDDEN, "cross-site request rejected")
            return False
        if not same_origin(self.headers.get("Origin"), self.headers.get("Host")):
            self._error(HTTPStatus.FORBIDDEN, "origin rejected")
            return False
        key = self.client_address[0]
        if not self.app.write_limiter.allow(key):
            self._error(HTTPStatus.TOO_MANY_REQUESTS, "write rate limit reached")
            return False
        return True

    def _json_body(self) -> dict[str, Any]:
        if (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("application/json is required")
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        if not 0 <= length <= MAX_REQUEST_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        return payload

    @staticmethod
    def _public(item: dict[str, Any], *, reveal: bool) -> dict[str, Any]:
        result = dict(item)
        result["address"] = item["address"] if reveal else mask_email(item["address"])
        return result

    def _serve_static(self, path: str) -> bool:
        name = STATIC_NAMES.get(path)
        if not name:
            return False
        target = self.app.static_root / name
        if not target.is_file():
            self._error(HTTPStatus.NOT_FOUND, "not found")
            return True
        content_type = (
            STATIC_TYPES.get(target.suffix.lower())
            or mimetypes.guess_type(name)[0]
            or "application/octet-stream"
        )
        self._send_bytes(HTTPStatus.OK, target.read_bytes(), content_type, cache="no-cache, max-age=0")
        return True

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._host_ok():
            return
        self._error(HTTPStatus.METHOD_NOT_ALLOWED, "cross-origin requests are not supported")

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_ok():
            return
        parsed = urlsplit(self.path)
        if self._serve_static(parsed.path):
            return
        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "service": "veil-garden"})
            return
        if not self._auth_ok():
            return
        if not self.app.read_limiter.allow(self.client_address[0]):
            self._error(HTTPStatus.TOO_MANY_REQUESTS, "read rate limit reached")
            return
        query = parse_qs(parsed.query, keep_blank_values=True)
        try:
            if parsed.path == "/api/bootstrap":
                reveal = query.get("reveal", ["0"])[0] == "1"
                aliases = [
                    self._public(item, reveal=reveal) for item in self.app.store.list_aliases(limit=500)
                ]
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "demo": self.app.config.demo,
                        "privacy": "revealed" if reveal else "masked",
                        "stats": self.app.store.stats(),
                        "aliases": aliases,
                        "events": self.app.store.events(limit=12),
                        "officialGuide": OFFICIAL_GUIDE,
                    },
                )
                return
            if parsed.path == "/api/aliases":
                reveal = query.get("reveal", ["0"])[0] == "1"
                status = clean_text(query.get("status", ["all"])[0], limit=16)
                search = clean_text(query.get("q", [""])[0], limit=120)
                limit = min(max(int(query.get("limit", ["100"])[0]), 1), 500)
                offset = max(int(query.get("offset", ["0"])[0]), 0)
                items = self.app.store.list_aliases(query=search, status=status, limit=limit, offset=offset)
                self._send_json(
                    HTTPStatus.OK, {"ok": True, "aliases": [self._public(x, reveal=reveal) for x in items]}
                )
                return
            if parsed.path == "/api/events":
                self._send_json(HTTPStatus.OK, {"ok": True, "events": self.app.store.events()})
                return
            if parsed.path == "/api/export":
                self._export(query)
                return
        except (ValueError, OverflowError):
            self._error(HTTPStatus.BAD_REQUEST, "invalid request")
            return
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "request could not be completed")
            return
        self._error(HTTPStatus.NOT_FOUND, "not found")

    def _export(self, query: dict[str, list[str]]) -> None:
        fmt = clean_text(query.get("format", ["csv"])[0], limit=8).lower()
        full = (self.headers.get("X-Export-Confirmation") or "") == "EXPORT FULL"
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            batch = self.app.store.list_aliases(limit=500, offset=offset)
            items.extend(batch)
            if len(batch) < 500:
                break
            offset += len(batch)
        rows = [self._public(item, reveal=full) for item in items]
        if fmt == "txt":
            body = ("\n".join(item["address"] for item in rows) + ("\n" if rows else "")).encode("utf-8")
            content_type = "text/plain; charset=utf-8"
            filename = "veil-garden.txt"
        elif fmt == "json":
            body = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            filename = "veil-garden.json"
        elif fmt == "csv":
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(["address", "label", "status", "tags", "note", "updated_at"])
            for item in rows:
                writer.writerow(
                    [
                        item["address"],
                        item["label"],
                        item["status"],
                        ", ".join(item["tags"]),
                        item["note"],
                        item["updated_at"],
                    ]
                )
            body = ("\ufeff" + output.getvalue()).encode("utf-8")
            content_type = "text/csv; charset=utf-8"
            filename = "veil-garden.csv"
        else:
            raise ValueError("unsupported export format")
        self._send_bytes(
            HTTPStatus.OK,
            body,
            content_type,
            disposition=f'attachment; filename="{filename}"',
        )

    def do_POST(self) -> None:  # noqa: N802
        self._write_request("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._write_request("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._write_request("DELETE")

    def _write_request(self, method: str) -> None:
        if not self._host_ok() or not self._auth_ok() or not self._write_guard():
            return
        path = urlsplit(self.path).path
        try:
            if method == "POST" and path == "/api/aliases":
                item = self.app.store.add(self._json_body())
                self._send_json(HTTPStatus.CREATED, {"ok": True, "alias": self._public(item, reveal=True)})
                return
            if method == "POST" and path == "/api/import":
                payload = self._json_body()
                rows = payload.get("aliases")
                if not isinstance(rows, list):
                    raise ValueError("aliases array required")
                normalized = [row if isinstance(row, dict) else {"address": row} for row in rows]
                result = self.app.store.import_many(normalized)
                self._send_json(HTTPStatus.OK, {"ok": True, **result})
                return
            prefix = "/api/aliases/"
            if path.startswith(prefix):
                alias_id = path[len(prefix) :]
                if not alias_id or "/" in alias_id or len(alias_id) > 32:
                    raise ValueError("invalid identifier")
                if method == "PATCH":
                    item = self.app.store.update(alias_id, self._json_body())
                    self._send_json(HTTPStatus.OK, {"ok": True, "alias": self._public(item, reveal=True)})
                    return
                if method == "DELETE":
                    confirmation = self.headers.get("X-Remove-Confirmation") or ""
                    if confirmation != f"REMOVE {alias_id}":
                        self._error(HTTPStatus.CONFLICT, "exact removal confirmation required")
                        return
                    self.app.store.remove(alias_id)
                    self._send_json(HTTPStatus.OK, {"ok": True})
                    return
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "record not found")
            return
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "request could not be completed")
            return
        self._error(HTTPStatus.NOT_FOUND, "not found")
