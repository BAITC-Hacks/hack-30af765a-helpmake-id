"""Tests for the postgres infrastructure module (no real DB required)."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.core.postgres import Session, get_engine, on_shutdown, on_startup, session


async def test_get_engine_returns_engine():
    engine = get_engine()
    import sqlalchemy.ext.asyncio

    assert isinstance(engine, sqlalchemy.ext.asyncio.AsyncEngine)


async def test_on_startup_initialises_engine():
    import src.core.postgres as pg_mod

    original = pg_mod._engine
    pg_mod._engine = None
    try:
        await on_startup()
        assert pg_mod._engine is not None
    finally:
        pg_mod._engine = original


async def test_on_shutdown_disposes_and_clears_engine():
    import src.core.postgres as pg_mod

    mock_engine = AsyncMock()
    pg_mod._engine = mock_engine
    await on_shutdown()
    mock_engine.dispose.assert_awaited_once()
    assert pg_mod._engine is None


async def test_on_shutdown_noop_when_no_engine():
    import src.core.postgres as pg_mod

    pg_mod._engine = None
    await on_shutdown()  # must not raise


async def test_check_connection_returns_true_on_success():
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )

    with patch('src.core.postgres.get_engine', return_value=mock_engine):
        from src.core.postgres import check_connection

        result = await check_connection()
    assert result is True


async def test_check_connection_returns_false_on_error():
    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(side_effect=Exception('connection refused'))

    with patch('src.core.postgres.get_engine', return_value=mock_engine):
        from src.core.postgres import check_connection

        result = await check_connection()
    assert result is False


async def test_session_decorator_passes_through_existing_session():
    """When first arg is a Session, the decorator reuses it."""
    received = []

    @session
    async def _fn(sess, value):
        received.append((sess, value))
        return value

    mock_session = MagicMock(spec=Session)
    result = await _fn(mock_session, 42)
    assert result == 42
    assert received[0][0] is mock_session


async def test_session_transaction_depth_tracking():
    """Verify _depth counter increments/decrements correctly."""
    mock_conn = AsyncMock()
    # Simulate context manager for begin()
    begin_cm = AsyncMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=False)
    mock_conn.begin = MagicMock(return_value=begin_cm)
    mock_conn.in_transaction = MagicMock(return_value=False)

    sess = Session(mock_conn)
    assert sess._depth == 0

    async with sess.transaction():
        assert sess._depth == 1

    assert sess._depth == 0


async def test_session_transaction_nested_uses_savepoint():
    """Verify nested transaction() calls use begin_nested (savepoint)."""
    mock_conn = AsyncMock()

    outer_cm = AsyncMock()
    outer_cm.__aenter__ = AsyncMock(return_value=None)
    outer_cm.__aexit__ = AsyncMock(return_value=False)

    inner_cm = AsyncMock()
    inner_cm.__aenter__ = AsyncMock(return_value=None)
    inner_cm.__aexit__ = AsyncMock(return_value=False)

    mock_conn.begin = MagicMock(return_value=outer_cm)
    mock_conn.begin_nested = MagicMock(return_value=inner_cm)

    sess = Session(mock_conn)
    async with sess.transaction(), sess.transaction():
        pass

    mock_conn.begin.assert_called_once()
    mock_conn.begin_nested.assert_called_once()


async def test_session_fetch_one_maps_row():
    mock_row = {'id': 1, 'name': 'test'}
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = mock_row

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    sess = Session(mock_conn)
    result = await sess.fetch_one('SELECT 1')
    assert result == mock_row


async def test_session_fetch_one_returns_none_when_empty():
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    sess = Session(mock_conn)
    result = await sess.fetch_one('SELECT 1')
    assert result is None


async def test_session_fetch_all_returns_list():
    mock_rows = [{'id': 1}, {'id': 2}]
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = mock_rows

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    sess = Session(mock_conn)
    result = await sess.fetch_all('SELECT 1')
    assert result == [{'id': 1}, {'id': 2}]


async def test_session_execute_delegates_to_conn():
    mock_result = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    sess = Session(mock_conn)
    result = await sess.execute('SELECT 1')
    assert result is mock_result
