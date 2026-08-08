# Changelog

## 1.0.1 — 2026-08-09

- Read authenticated write bodies once, within the 256 KiB limit, before Origin, content-type, and business validation so Windows HTTP clients reliably receive the intended error response instead of an occasional connection reset.
- Repeat the cross-port rejection contract in tests and confirm that rejected requests cannot create local records.

## 1.0.0 — 2026-08-09

- Initial stable release.
- Local SQLite catalog with manual add, TXT/CSV import, labels, notes, active/resting state, search, deduplication, and privacy-safe events.
- Masked-by-default browsing and export; explicit reveal, confirmed full export, and confirmed local removal.
- Memory-only browser access token, exact Host/Origin controls, CSP, request limits, and rate limiting.
- Sky, Jade, Sunset, and Graphite themes with desktop and mobile layouts.
- Local, Docker, systemd, SSH-tunnel, and HTTPS reverse-proxy deployment paths.
- Explicit exclusion of Apple credentials, private APIs, and automated address creation.
