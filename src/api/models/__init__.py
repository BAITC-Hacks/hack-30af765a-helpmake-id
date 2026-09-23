"""Models package.

Import every domain model module here so their SQLAlchemy Tables are
registered with postgres.metadata before Alembic and tests read it.

Add domain models as they are created::

    from . import entity   # noqa: F401
"""
