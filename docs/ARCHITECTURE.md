# Architecture

```text
Browser (native HTML/CSS/JS)
  │ same-origin Bearer API
  ▼
ThreadingHTTPServer
  ├─ Host / Origin / Fetch Metadata guards
  ├─ body limits and per-client rate limits
  ├─ masked read model and confirmed full export
  ▼
AliasStore
  └─ local SQLite (aliases + privacy-safe event summaries)
```

## Decisions

- **No Apple integration:** address creation and Apple-side state stay in Apple's official interface. This removes Apple credentials, undocumented authentication, automation fragility, and private service endpoints from the trust boundary.
- **Standard-library runtime:** `http.server`, `sqlite3`, and native browser assets keep installation small and auditable. `ThreadingHTTPServer` is suitable for a personal self-hosted workbench, not a high-volume multi-tenant service.
- **Server-owned persistence:** the browser never receives a database file. Addresses are masked by default; revealing is an authenticated, explicit view state.
- **Memory-only browser token:** a generated local token arrives in the URL fragment, is read once, then removed. Only the theme name is persisted in `localStorage`.
- **Local state semantics:** active/resting and removal operate solely on the local catalog. They never claim to represent or mutate Apple-side state automatically.
- **No hidden network path:** CSP restricts runtime connections to the same origin. The only external URL is a user-clicked Apple Support link.

## Limits

- One process owns one SQLite database. Writes are serialized with an application lock and SQLite transactions.
- A list response is capped at 500 records and an import at 5,000 records / 256 KiB.
- Events retain at most 200 generic summaries and never include an address.
- The SQLite database is plaintext; deployment security depends on OS permissions, encrypted storage, backups, HTTPS, and token custody.

