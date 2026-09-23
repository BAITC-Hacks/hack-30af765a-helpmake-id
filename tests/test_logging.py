"""Tests for structured logging utilities."""

import logging


def test_json_formatter_basic():
    from src.core.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='hello %s',
        args=('world',),
        exc_info=None,
    )
    output = formatter.format(record)
    import json

    parsed = json.loads(output)
    assert parsed['level'] == 'INFO'
    assert parsed['logger'] == 'test'
    assert parsed['message'] == 'hello world'


def test_json_formatter_with_extra():
    from src.core.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name='test',
        level=logging.WARNING,
        pathname='',
        lineno=0,
        msg='test message',
        args=(),
        exc_info=None,
    )
    record.request_id = 'abc-123'
    record.path = '/api/v1/health'
    output = formatter.format(record)
    import json

    parsed = json.loads(output)
    assert parsed['request_id'] == 'abc-123'
    assert parsed['path'] == '/api/v1/health'


def test_json_formatter_strips_sensitive_keys():
    from src.core.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='test',
        args=(),
        exc_info=None,
    )
    record.token = 'secret-token'
    record.password = 'hunter2'
    output = formatter.format(record)
    import json

    parsed = json.loads(output)
    assert 'token' not in parsed
    assert 'password' not in parsed


def test_json_formatter_with_exception():
    from src.core.logging import JSONFormatter

    formatter = JSONFormatter()
    try:
        raise ValueError('test error')
    except ValueError:
        import sys

        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name='test',
        level=logging.ERROR,
        pathname='',
        lineno=0,
        msg='error occurred',
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    import json

    parsed = json.loads(output)
    assert 'exc_info' in parsed
    assert 'ValueError' in parsed['exc_info']


def test_human_formatter():
    from src.core.logging import HumanFormatter

    formatter = HumanFormatter()
    record = logging.LogRecord(
        name='test',
        level=logging.DEBUG,
        pathname='',
        lineno=0,
        msg='debug message',
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert 'debug message' in output
    assert 'test' in output


def test_configure_logging_development():
    # Override settings for this test
    import unittest.mock

    from src.core.config import Settings
    from src.core.logging import configure_logging

    mock_settings = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        APP_ENV='development',
        LOG_LEVEL='DEBUG',
    )
    with unittest.mock.patch(
        'src.core.logging.config.get_settings', return_value=mock_settings
    ):
        configure_logging()

    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_configure_logging_production():
    import unittest.mock

    from src.core.config import Settings
    from src.core.logging import JSONFormatter, configure_logging

    mock_settings = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        APP_ENV='production',
        LOG_LEVEL='INFO',
    )
    with unittest.mock.patch(
        'src.core.logging.config.get_settings', return_value=mock_settings
    ):
        configure_logging()

    root = logging.getLogger()
    assert any(isinstance(h.formatter, JSONFormatter) for h in root.handlers)
