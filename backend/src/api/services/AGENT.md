# Service Conventions

These instructions apply to `src/api/services/`.

`services/` hosts **process-hosted runtime services only**. It is not an
application-service layer and must not accumulate business logic. See
`src/api/CLAUDE.md` for the full layer contract.

## Purpose

A module here exists to run a long-lived process. It owns:

- Worker lifecycle (`on_start`, `on_stop`, dependency wiring).
- Startup and shutdown.
- Scheduling and periodic invocation.
- Health/liveness integration.

## Required Pattern

- A service is **thin**: it schedules or triggers a unit of work and invokes a
  **controller** for the actual business work. It does not implement the use case.
- No SQL, no SQLAlchemy statements, no `session.fetch_*`/`session.execute`.
- No business rules, state machines, or transaction scopes — those live in controllers.

```python
# services/sync.py — lifecycle + scheduling only
class SyncService(services.worker.Service):
    async def on_start(self) -> None:
        await self.periodic_scheduler.schedule_task(
            self.sync,
            interval=self.config.sync_interval,
        )

    async def sync(self) -> None:
        # delegate one unit of work to the controller
        await controllers.entity.sync_entities()
```

The service retains the worker and scheduler; the synchronization use case
belongs in `controllers/<domain>.py`.

## Must Not Contain

- Business rules or use-case implementations.
- Application SQL or direct table access.
- Provider request/response construction (that is a webhook/provider adapter).
- Anything that belongs in a controller.

## Summary

| Allowed | Not Allowed |
|---|---|
| Worker lifecycle hooks | Business logic |
| Periodic scheduling | SQL/SQLAlchemy |
| Calling a controller | Provider adapters |
| Health/liveness hooks | Transaction scopes |
