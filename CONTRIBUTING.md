# Contributing

Small, focused pull requests are welcome.

1. Keep Apple authentication, passwords, 2FA, cookies, private APIs, browser automation, and address-generation automation out of scope.
2. Use only reserved synthetic domains in code, tests, screenshots, issues, and fixtures.
3. Preserve masked-by-default behavior, exact Host/Origin checks, memory-only browser tokens, four global themes, and local/server deployment support.
4. Run:

   ```bash
   python -m unittest discover -s tests -v
   ruff check .
   ruff format --check .
   bandit -r src -ll
   ```

5. Update both READMEs when behavior changes. Security-sensitive reports belong in GitHub Private Vulnerability Reporting, not a public issue.

