# Webhook Conventions

These instructions apply to `src/api/webhooks/`.

Modules here are **external protocol adapters** — the boundary between a provider
and our controllers. They translate between provider wire formats and our domain,
and nothing more. See `src/api/CLAUDE.md` for the full layer contract.

## Purpose

Both inbound and outbound adapters live here.

Owns:

- Authentication (API keys, basic auth, signature checks).
- Request/query parsing and external schema normalization.
- Sensitive-field removal and boundary-safe logging.
- Provider payload construction and outbound HTTP transport.
- Provider-specific response mapping (result codes, messages, locale, cache-control).

## Required Pattern

- **Inbound adapters call controllers.** They do not implement business state
  machines; they map controller outcomes to the provider's response format.
- If provider response mapping must catch a domain exception, catch the
  model-owned exception through a documented controller-package re-export.
  Do not declare a duplicate webhook exception or import `models/` directly.
- **Outbound adapters build and send payloads.** They own no persistence or
  business state. They build event payloads and post them via an HTTP client
  (e.g. `httpx`), with no DB access.
- Pass provider-neutral values rather than importing model table definitions.

```python
# inbound flow
v1 webhook route
    → webhooks.<provider>      # authenticate, parse, map response
        → controllers.<domain> # business decisions + orchestration
            → models.<domain>  # SQLAlchemy, sessions, transactions
```

## Must Not Contain

- SQL, `session.fetch_*`/`session.execute`, or SQLAlchemy statements.
- Database transactions or `@postgres.session`.
- Business state machines, transition decisions, or event-emission orchestration
  (move these to a controller).
- Direct model-table access. Inbound adapters reach persistence only through a
  controller.

## Summary

| Allowed | Not Allowed |
|---|---|
| Auth / signature verification | SQL / database access |
| Payload parsing & normalization | Business state machines |
| Outbound HTTP calls | Transaction scopes |
| Provider response mapping | Domain exception declarations |
| Boundary-safe logging | Direct model table imports |
