# Security policy

## Supported versions

Security fixes are provided for the latest release on `main`.

## Reporting

Use GitHub **Private Vulnerability Reporting** for vulnerabilities. Do not open a public issue containing an alias, access token, database, export, server address, filesystem path, or private screenshot.

Include a minimal reproduction with reserved domains such as `example.invalid`, the affected version, deployment shape, and expected impact. Never send Apple Account credentials or verification codes; Veil Garden does not need them.

## Deployment baseline

- Keep the default loopback bind for local use.
- CSV exports neutralize spreadsheet formula prefixes. Direct HTTP mode limits worker threads and applies a socket deadline; internet deployments must still keep the application behind the documented HTTPS reverse proxy.
- Use an SSH tunnel or HTTPS reverse proxy for remote access.
- Use a unique access token of at least 24 characters and an exact Host allowlist.
- Restrict and encrypt the SQLite database and backups.
- Never publish `.env`, `data/`, exports, proxy logs, or screenshots containing real addresses.

See [`docs/PRIVACY.md`](./docs/PRIVACY.md) for the complete trust boundary.
