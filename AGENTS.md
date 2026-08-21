# Hide My Email manager project rules

- Read the workspace root `README.md` and this file before changing the project.
- Preserve the product boundary: Hide My Email manager organizes user-provided records only. Never add Apple password, 2FA, cookie, session, trust-token, private API, scraping, browser automation, or automatic address creation flows.
- Use reserved synthetic domains in tests, screenshots, logs, documentation, and examples. Never commit `.env`, databases, exports, addresses, tokens, host identities, paths, or deployment logs.
- Keep the browser token memory-only; only the theme may be persisted. Keep masking on by default and exact confirmation for full export and local removal.
- Maintain the four global themes, `#17191d` Graphite background, top-right controls, SVG/PNG/ICO favicons, responsive desktop/mobile UI, and local/server deployment paths.
- Update Chinese and English documentation together. Any public change also requires the workspace root `README.md` and profile repository to be checked and synchronized.
- Before release, run tests, Ruff, Bandit, pip-audit, detect-secrets, Gitleaks on the tree and complete history, fresh-clone packaging checks, real browser QA, link/image checks, and GitHub online verification.

