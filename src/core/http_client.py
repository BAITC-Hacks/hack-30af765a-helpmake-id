import httpx

from . import config

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError('HTTP client not initialized — call on_startup first')
    return _client


async def on_startup() -> None:
    global _client
    settings = config.get_settings()
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.HTTP_CLIENT_TIMEOUT),
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
        ),
    )


async def on_shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
