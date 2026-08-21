# Hide My Email manager

<p align="center">
  <img src="./docs/images/social-preview.png" alt="Hide My Email manager — organize your Apple aliases" width="100%" />
</p>

<p align="center">
  <a href="./README.md">中文</a> · English
</p>

<p align="center">
  <a href="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/ci.yml"><img src="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/codeql.yml"><img src="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/codeql.yml/badge.svg" alt="CodeQL" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-287f87" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-5f7f55.svg" alt="License: MIT" />
</p>

> Create enough Apple Hide My Email addresses and you stop remembering which one went where. This keeps track.

## Why this exists

iCloud+ Hide My Email is genuinely good: generate a random address per signup, forwarded to your real inbox.

The problem shows up six months later. You have forty addresses that look like `quiet-leaf-3f2a@icloud.com`, and Apple's interface only lets you page through them — no labels, no notes, no bulk search, no way to take them with you. "Which service was this one for?" You don't remember.

This is the notebook: **import, label, annotate, mark status, search, back up.** The addresses are still created by you in Apple's own interface; this just makes them memorable.

**It does not take over your Apple account.** No Apple password, verification code, cookie, or token is accepted, and no undocumented Apple API is called.

[Deployment](./docs/DEPLOYMENT.md) · [Privacy and security](./docs/PRIVACY.md) · [Issues](https://github.com/ferretgeek/hide-my-email-manager/issues)

## Interface

<p align="center">
  <img src="./docs/images/dashboard.png" alt="Address list interface" width="100%" />
</p>

<p align="center">
  <img src="./docs/images/intro.png" alt="Entry point and product boundaries" width="100%" />
</p>

## What it does

- **Organizes, doesn't take over** — add manually or bulk-import from TXT / CSV; it never signs in to Apple or creates addresses for you.
- **Holds the line by default** — addresses are masked on screen, a full export requires typing an exact confirmation phrase, and the access token lives only in the current page's memory.
- **Actually usable** — search, labels, notes, in-use / dormant status, duplicate filtering, event history, and CSV / JSON / TXT export.
- **Local or server** — runs on the Python standard library, with Docker, systemd, and HTTPS reverse-proxy configurations provided.
- **Four global themes** — Azure, Emerald, Sunset, and `#17191d` deep gray, fully responsive on desktop and mobile.

## The boundaries, stated plainly

| It will | It never will |
| --- | --- |
| Store addresses, labels, and notes you provide | Request or store an Apple password, 2FA code, cookie, session, or trust token |
| Mark "in use / dormant" in a local database | Change state on Apple's side, auto-create addresses, or bypass platform limits |
| Point you to Apple's official pages for actions on their side | Reimplement Apple's private web auth or internal APIs |
| Produce masked exports by default, full export on explicit confirmation | Upload addresses, the database, or tokens to a third party |

Apple's own creation and management steps are documented at [Apple Support](https://support.apple.com/guide/icloud/create-and-edit-addresses-mm1a876f7aed/icloud).

## Running locally

Requires Python 3.10 or later.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install .
veil-garden
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install .
veil-garden
```

The terminal prints a local address with a `#token=...` fragment. **URL fragments are never sent to the server**; the frontend reads it, immediately removes it from the address bar, and writes it to neither `localStorage` nor `sessionStorage`.

To look at synthetic data first:

```bash
veil-garden --demo
```

The demo uses only the reserved domain `example.invalid` and touches no real address.

## Import format

The simplest TXT is one address per line; you can add your own name and labels:

```text
quiet.leaf@example.com
paper.lantern@example.com | Reading subscriptions | reading,weekly
```

The server accepts at most 5,000 records and a 256 KiB body per request, and deduplicates addresses case-insensitively. Status, labels, and notes are local only and **never sync to Apple.**

## Server deployment

Public access must sit behind an HTTPS reverse proxy, with a strong access token of at least 24 characters and an exact Host allowlist.

```bash
cp .env.example .env
python -m veil_garden token
docker compose up -d --build
```

Put the generated value in `VEIL_ACCESS_TOKEN` in `.env`, then configure an SSH tunnel or HTTPS as described in the [deployment guide](./docs/DEPLOYMENT.md). Never commit `.env`, `data/`, the SQLite database, or export files.

## Worth noting technically

**The access token travels in a URL fragment.** Fragments are never sent to the server, so the token can't appear in reverse-proxy or access logs. The frontend strips it from the address bar immediately and writes it to no browser storage.

**Imports are bounded.** At most 5,000 records and a 256 KiB body per request. A "bulk import" endpoint without a ceiling is a denial-of-service endpoint.

**Full export requires a confirmation phrase.** The default export is masked. Getting a plaintext address list means typing an exact phrase each time — because that file is itself a high-value target.

**The database is not a vault, and the docs say so.** Production mode uses `data/veil-garden.sqlite3`, which contains full addresses and notes. **It is not an encrypted vault.** Restrict file permissions and enable encryption on the disk or backups. Saying that in the README is more responsible than pretending otherwise.

**Standard library only.** Runtime code uses only the Python standard library, and the browser UI is plain HTML / CSS / JavaScript with no third-party runtime assets.

## What it doesn't do

- It doesn't sign in to Apple, create addresses, or change any state on Apple's side.
- "Dormant" and "removed" **only change the local record.** To disable, restore, or delete an address at Apple, use Apple's interface.
- No telemetry, ads, cloud sync, or third-party runtime assets.

## Development and verification

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -r src -ll
```

Release gates additionally include pip-audit, detect-secrets, Gitleaks (working tree and full history), a clean clone, wheel installation, real desktop and mobile rendering, image metadata checks, and a review of public GitHub settings. See [release audit](./docs/发布审计.md).

## More documentation

[Deployment](./docs/DEPLOYMENT.md) · [Architecture](./docs/ARCHITECTURE.md) · [Privacy and security](./docs/PRIVACY.md) · [Release audit](./docs/发布审计.md) · [Changelog](./CHANGELOG.md) · [Contributing](./CONTRIBUTING.md) · [Security policy](./SECURITY.md)

## License and disclaimer

Original code is released under the [MIT License](./LICENSE).

Apple, iCloud, iCloud+, Hide My Email, and related marks belong to their respective owners; this license grants no rights to any third-party brand or service. This is an independent, unofficial community tool with no affiliation with, authorization from, or endorsement by Apple.
