"""Services package.

A service is a thin process-lifecycle wrapper. It schedules periodic work
and delegates to controllers. Business logic must not accumulate here.

Add services as they are created::

    src/api/services/sync.py   — periodic synchronization
    src/api/services/worker.py — background worker
"""
