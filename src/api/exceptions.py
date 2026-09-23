import typing


class AppException(Exception):
    """Base class for all application HTTP exceptions.

    Raised from controllers and caught by the exception handler in main.py.
    The handler emits a flat JSON body: {"detail": "...", ...extra}.
    """

    status_code: int = 500
    default_detail: str = 'An unexpected error occurred'

    def __init__(
        self,
        detail: str | None = None,
        **extra: typing.Any,
    ) -> None:
        self.detail = detail or self.default_detail
        self.extra = extra
        super().__init__(self.detail)

    def response_body(self) -> dict[str, typing.Any]:
        body: dict[str, typing.Any] = {'detail': self.detail}
        body.update(self.extra)
        return body


class HTTPBadRequestException(AppException):
    status_code = 400
    default_detail = 'Bad request'

    def __init__(
        self,
        detail: str | None = None,
        status: typing.Any = None,
        **extra: typing.Any,
    ) -> None:
        if status is not None:
            extra['status'] = status if isinstance(status, str) else status.value
        super().__init__(detail=detail, **extra)


class HTTPUnauthorizedException(AppException):
    status_code = 401
    default_detail = 'Authentication required'


class HTTPForbiddenException(AppException):
    status_code = 403
    default_detail = 'You do not have permission to perform this action'


class HTTPNotFoundException(AppException):
    status_code = 404
    default_detail = 'The requested resource was not found'


class HTTPConflictException(AppException):
    status_code = 409
    default_detail = 'Conflict'


class HTTPUnprocessableException(AppException):
    status_code = 422
    default_detail = 'Unprocessable entity'


class HTTPInternalServerException(AppException):
    status_code = 500
    default_detail = 'Internal server error'
