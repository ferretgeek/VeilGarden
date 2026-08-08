from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from veil_garden.config import AppConfig, ConfigError


class ConfigTests(unittest.TestCase):
    def test_loopback_generates_ephemeral_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig.from_env()
        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertTrue(config.generated_access_token)
        self.assertGreaterEqual(len(config.access_token), 24)
        self.assertIn("localhost", config.allowed_hosts)

    def test_explicit_token_is_preserved(self) -> None:
        token = "v" * 32
        with patch.dict(os.environ, {"VEIL_ACCESS_TOKEN": token}, clear=True):
            config = AppConfig.from_env()
        self.assertEqual(config.access_token, token)
        self.assertFalse(config.generated_access_token)

    def test_short_token_is_rejected(self) -> None:
        with (
            patch.dict(os.environ, {"VEIL_ACCESS_TOKEN": "too-short"}, clear=True),
            self.assertRaisesRegex(ConfigError, "24"),
        ):
            AppConfig.from_env()

    def test_non_loopback_http_is_rejected_by_default(self) -> None:
        env = {
            "VEIL_BIND_HOST": "0.0.0.0",
            "VEIL_ACCESS_TOKEN": "x" * 32,
            "VEIL_ALLOWED_HOSTS": "garden.example.com",
        }
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ConfigError, "non-loopback"):
            AppConfig.from_env()

    def test_private_http_requires_explicit_hosts(self) -> None:
        env = {
            "VEIL_BIND_HOST": "0.0.0.0",
            "VEIL_ACCESS_TOKEN": "x" * 32,
            "VEIL_ALLOW_PRIVATE_HTTP": "1",
        }
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ConfigError, "ALLOWED_HOSTS"):
            AppConfig.from_env()

    def test_wildcard_allowed_host_is_rejected(self) -> None:
        env = {
            "VEIL_BIND_HOST": "0.0.0.0",
            "VEIL_ACCESS_TOKEN": "x" * 32,
            "VEIL_ALLOW_PRIVATE_HTTP": "1",
            "VEIL_ALLOWED_HOSTS": "*",
        }
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ConfigError, "exact"):
            AppConfig.from_env()

    def test_port_bounds_are_enforced(self) -> None:
        with (
            patch.dict(os.environ, {"VEIL_ACCESS_TOKEN": "x" * 32, "VEIL_PORT": "70000"}, clear=True),
            self.assertRaisesRegex(ConfigError, "between"),
        ):
            AppConfig.from_env()

    def test_demo_override_wins(self) -> None:
        with patch.dict(os.environ, {"VEIL_ACCESS_TOKEN": "x" * 32, "VEIL_DEMO": "0"}, clear=True):
            config = AppConfig.from_env(demo_override=True)
        self.assertTrue(config.demo)


if __name__ == "__main__":
    unittest.main()
