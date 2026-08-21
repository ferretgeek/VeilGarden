from __future__ import annotations

import csv
import io
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from veil_garden.app import VeilGardenServer, _GardenHTTPServer
from veil_garden.config import AppConfig
from veil_garden.store import AliasStore


class AppTests(unittest.TestCase):
    TOKEN = "test-access-token-that-is-long-enough"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        config = AppConfig(
            bind_host="127.0.0.1",
            port=0,
            access_token=self.TOKEN,
            generated_access_token=False,
            allowed_hosts=frozenset({"127.0.0.1", "localhost"}),
            data_dir=Path(self.temp.name),
            demo=False,
            allow_private_http=False,
        )
        self.store = AliasStore(":memory:")
        self.app = VeilGardenServer(config, store=self.store)
        self.httpd = _GardenHTTPServer(("127.0.0.1", 0), self.app)
        self.app.httpd = self.httpd
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.store.close()
        self.temp.cleanup()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
        auth: bool = True,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        request_headers = dict(headers or {})
        if auth:
            request_headers["Authorization"] = f"Bearer {self.TOKEN}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data, headers=request_headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as response:  # noqa: S310
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read(), dict(exc.headers)

    def write_headers(self) -> dict[str, str]:
        return {"Origin": f"http://127.0.0.1:{self.port}", "Sec-Fetch-Site": "same-origin"}

    def add_alias(self, address: str = "leaf@example.com") -> dict:
        status, body, _headers = self.request(
            "/api/aliases",
            method="POST",
            payload={"address": address, "label": "Reading", "tags": ["weekly"]},
            headers=self.write_headers(),
        )
        self.assertEqual(status, 201)
        return json.loads(body)["alias"]

    def test_health_is_public(self) -> None:
        status, body, _headers = self.request("/health", auth=False)
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_static_page_is_public_with_security_headers(self) -> None:
        status, body, headers = self.request("/", auth=False)
        self.assertEqual(status, 200)
        self.assertIn("隐私邮箱地址".encode(), body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_svg_uses_browser_safe_mime_type(self) -> None:
        status, body, headers = self.request("/favicon.svg", auth=False)
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("image/svg+xml"))
        self.assertTrue(body.startswith(b"<svg"))

    def test_bootstrap_requires_exact_bearer_token(self) -> None:
        status, _body, headers = self.request("/api/bootstrap", auth=False)
        self.assertEqual(status, 401)
        self.assertEqual(headers["WWW-Authenticate"], "Bearer")
        status, _body, _headers = self.request(
            "/api/bootstrap", auth=False, headers={"Authorization": f"bearer {self.TOKEN}"}
        )
        self.assertEqual(status, 401)

    def test_invalid_host_is_rejected(self) -> None:
        status, body, _headers = self.request("/health", auth=False, headers={"Host": "evil.example"})
        self.assertEqual(status, 400)
        self.assertNotIn(b"evil.example", body)

    def test_cross_origin_write_is_rejected(self) -> None:
        status, _body, _headers = self.request(
            "/api/aliases",
            method="POST",
            payload={"address": "leaf@example.com"},
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(self.store.stats()["total"], 0)

    def test_cross_port_write_is_rejected(self) -> None:
        for _attempt in range(3):
            status, _body, _headers = self.request(
                "/api/aliases",
                method="POST",
                payload={"address": "leaf@example.com"},
                headers={"Origin": "http://127.0.0.1:9", "Sec-Fetch-Site": "same-origin"},
            )
            self.assertEqual(status, 403)
        self.assertEqual(self.store.stats()["total"], 0)

    def test_options_does_not_grant_cors(self) -> None:
        status, _body, headers = self.request("/api/aliases", method="OPTIONS", auth=False)
        self.assertEqual(status, 405)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_json_content_type_is_required(self) -> None:
        status, _body, _headers = self.request(
            "/api/aliases",
            method="POST",
            payload={"address": "leaf@example.com"},
            headers={**self.write_headers(), "Content-Type": "text/plain"},
        )
        self.assertEqual(status, 400)

    def test_create_list_mask_and_reveal(self) -> None:
        self.add_alias()
        status, body, _headers = self.request("/api/bootstrap")
        masked = json.loads(body)["aliases"][0]["address"]
        self.assertEqual(status, 200)
        self.assertNotEqual(masked, "leaf@example.com")
        status, body, _headers = self.request("/api/bootstrap?reveal=1")
        self.assertEqual(json.loads(body)["aliases"][0]["address"], "leaf@example.com")

    def test_update_alias(self) -> None:
        item = self.add_alias()
        status, body, _headers = self.request(
            f"/api/aliases/{item['id']}",
            method="PATCH",
            payload={"status": "resting", "label": "Archive"},
            headers=self.write_headers(),
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["alias"]["status"], "resting")

    def test_import_is_bounded_and_counts_invalid(self) -> None:
        status, body, _headers = self.request(
            "/api/import",
            method="POST",
            payload={"aliases": ["one@example.com", "ONE@example.com", "invalid"]},
            headers=self.write_headers(),
        )
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual((result["imported"], result["duplicates"], result["invalid"]), (1, 1, 1))

    def test_masked_export_is_default(self) -> None:
        self.add_alias()
        status, body, headers = self.request("/api/export?format=txt")
        self.assertEqual(status, 200)
        self.assertNotIn(b"leaf@example.com", body)
        self.assertIn("attachment", headers["Content-Disposition"])

    def test_full_export_requires_exact_confirmation(self) -> None:
        self.add_alias()
        status, body, _headers = self.request(
            "/api/export?format=json", headers={"X-Export-Confirmation": "EXPORT FULL"}
        )
        self.assertEqual(status, 200)
        self.assertIn(b"leaf@example.com", body)
        status, body, _headers = self.request(
            "/api/export?format=json", headers={"X-Export-Confirmation": "export full"}
        )
        self.assertNotIn(b"leaf@example.com", body)

    def test_export_includes_records_after_first_page(self) -> None:
        self.store.import_many([{"address": f"leaf-{index}@example.com"} for index in range(501)])
        status, body, _headers = self.request(
            "/api/export?format=txt", headers={"X-Export-Confirmation": "EXPORT FULL"}
        )
        self.assertEqual(status, 200)
        self.assertIn(b"leaf-500@example.com", body)

    def test_csv_export_neutralizes_formula_prefixes(self) -> None:
        self.store.add(
            {
                "address": "leaf@example.com",
                "label": '=HYPERLINK("https://example.invalid")',
                "note": " @SUM(A1:A2)",
            }
        )
        status, body, _headers = self.request("/api/export?format=csv")
        self.assertEqual(status, 200)
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
        self.assertTrue(rows[0]["label"].startswith("'"))
        self.assertTrue(rows[0]["note"].startswith("'"))

    def test_server_bounds_connections_and_sets_socket_timeout(self) -> None:
        self.assertEqual(self.httpd.request_queue_size, 5)
        self.assertEqual(self.httpd.connection_slots._value, 64)
        status, _body, _headers = self.request("/health", auth=False)
        self.assertEqual(status, 200)
        deadline = time.monotonic() + 1
        while self.httpd.connection_slots._value != 64 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.httpd.connection_slots._value, 64)

    def test_remove_requires_exact_confirmation(self) -> None:
        item = self.add_alias()
        path = f"/api/aliases/{item['id']}"
        status, _body, _headers = self.request(path, method="DELETE", headers=self.write_headers())
        self.assertEqual(status, 409)
        self.assertEqual(self.store.stats()["total"], 1)
        status, _body, _headers = self.request(
            path,
            method="DELETE",
            headers={**self.write_headers(), "X-Remove-Confirmation": f"REMOVE {item['id']}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.store.stats()["total"], 0)

    def test_not_found_does_not_echo_path(self) -> None:
        status, body, _headers = self.request("/api/private-looking-value")
        self.assertEqual(status, 404)
        self.assertNotIn(b"private-looking-value", body)

    def test_internal_error_does_not_echo_exception(self) -> None:
        original = self.store.stats
        self.store.stats = lambda: (_ for _ in ()).throw(RuntimeError("private-database-path"))  # type: ignore[method-assign]
        try:
            status, body, _headers = self.request("/api/bootstrap")
        finally:
            self.store.stats = original  # type: ignore[method-assign]
        self.assertEqual(status, 500)
        self.assertNotIn(b"private-database-path", body)


if __name__ == "__main__":
    unittest.main()
