"""Tests for error handling and exception formatting."""

from src.api import exceptions


def test_app_exception_default_detail():
    exc = exceptions.AppException()
    assert exc.detail == 'An unexpected error occurred'
    assert exc.status_code == 500


def test_app_exception_custom_detail():
    exc = exceptions.AppException(detail='custom error')
    assert exc.detail == 'custom error'


def test_app_exception_response_body():
    exc = exceptions.AppException(detail='something went wrong')
    body = exc.response_body()
    assert body == {'detail': 'something went wrong'}


def test_app_exception_response_body_with_extra():
    exc = exceptions.HTTPBadRequestException(
        detail='bad input',
        status='name_conflict',
    )
    body = exc.response_body()
    assert body['detail'] == 'bad input'
    assert body['status'] == 'name_conflict'


def test_bad_request_exception():
    exc = exceptions.HTTPBadRequestException(detail='nope')
    assert exc.status_code == 400


def test_bad_request_exception_with_enum_status():

    from src.api.responses import Status

    class MyStatus(Status):
        DUPLICATE = 'duplicate_value'

    exc = exceptions.HTTPBadRequestException(
        detail='Already exists',
        status=MyStatus.DUPLICATE,
    )
    assert exc.extra['status'] == 'duplicate_value'


def test_unauthorized_exception():
    exc = exceptions.HTTPUnauthorizedException()
    assert exc.status_code == 401


def test_forbidden_exception():
    exc = exceptions.HTTPForbiddenException()
    assert exc.status_code == 403


def test_not_found_exception():
    exc = exceptions.HTTPNotFoundException()
    assert exc.status_code == 404


def test_conflict_exception():
    exc = exceptions.HTTPConflictException()
    assert exc.status_code == 409


def test_internal_server_exception():
    exc = exceptions.HTTPInternalServerException()
    assert exc.status_code == 500


async def test_app_exception_handler_returns_json(client):
    """Unhandled AppException -> flat JSON, no stack trace."""

    from src.main import app

    @app.get('/test-error-handler')
    async def _raise():
        raise exceptions.HTTPNotFoundException(detail='thing not found')

    resp = await client.get('/test-error-handler')
    assert resp.status_code == 404
    body = resp.json()
    assert body['detail'] == 'thing not found'
    assert 'traceback' not in body
    assert 'stack' not in body


async def test_generic_exception_handler_returns_500(client):
    from src.main import app

    @app.get('/test-generic-error')
    async def _raise_generic():
        raise RuntimeError('something internal blew up')

    resp = await client.get('/test-generic-error')
    assert resp.status_code == 500
    body = resp.json()
    assert 'detail' in body
    assert 'blew up' not in body['detail']


def test_responses_gen_responses():
    from src.api import responses

    result = responses.gen_responses(
        [
            responses.APIResponseNotFound,
            responses.APIResponseBadRequest,
        ]
    )
    assert 404 in result
    assert 400 in result
    assert result[404]['model'] is responses.APIResponseNotFound
