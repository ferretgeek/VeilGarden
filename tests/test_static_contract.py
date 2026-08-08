from __future__ import annotations

import unittest
from importlib.resources import files


class StaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = files("veil_garden").joinpath("static")
        cls.html = root.joinpath("index.html").read_text(encoding="utf-8")
        cls.css = root.joinpath("styles.css").read_text(encoding="utf-8")
        cls.js = root.joinpath("app.js").read_text(encoding="utf-8")

    def test_four_global_themes_exist(self) -> None:
        for theme in ("sky", "jade", "sunset", "graphite"):
            self.assertIn(f'data-theme-choice="{theme}"', self.html)
            if theme != "sky":
                self.assertIn(f'data-theme="{theme}"', self.css)

    def test_graphite_uses_required_deep_gray(self) -> None:
        self.assertIn("--bg: #17191d", self.css)

    def test_favicon_formats_are_linked(self) -> None:
        self.assertIn('href="/favicon.svg?v=1.0.0"', self.html)
        self.assertIn('href="/favicon.ico?v=1.0.0"', self.html)
        self.assertIn('href="/apple-touch-icon.png?v=1.0.0"', self.html)

    def test_no_external_runtime_assets(self) -> None:
        self.assertNotIn('<script src="http', self.html)
        self.assertNotIn('<link rel="stylesheet" href="http', self.html)

    def test_csp_compatible_assets_have_no_inline_script(self) -> None:
        self.assertNotIn("<script>", self.html)
        self.assertNotIn(" onclick=", self.html)

    def test_untrusted_values_are_not_inserted_as_html(self) -> None:
        self.assertNotIn("innerHTML", self.js)
        self.assertIn("textContent", self.js)

    def test_access_token_is_not_persisted(self) -> None:
        self.assertNotIn('localStorage.setItem("token"', self.js)
        self.assertNotIn('sessionStorage.setItem("token"', self.js)
        self.assertIn('localStorage.setItem("veil-garden-theme"', self.js)

    def test_icon_buttons_have_accessible_names(self) -> None:
        self.assertIn('aria-label="揭开地址遮罩"', self.html)
        self.assertIn('aria-label="选择主题，当前天青"', self.html)
        self.assertIn("重新遮罩地址", self.js)

    def test_official_boundary_is_visible(self) -> None:
        self.assertIn("NO PASSWORDS · NO TOKENS · NO PRIVATE API", self.html)
        self.assertIn("Apple 账户互不联动", self.html)

    def test_reduced_motion_and_mobile_breakpoints_exist(self) -> None:
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("@media (max-width: 640px)", self.css)


if __name__ == "__main__":
    unittest.main()
