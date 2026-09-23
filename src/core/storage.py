"""File storage abstraction.

Add a backend class here for each storage target (local, S3-compatible, GCS).
Wire the desired backend in src/main.py during application startup.

Accepted file types are validated at the API boundary (endpoint or schema).
"""

import abc
import pathlib
import re
import typing


class StorageError(Exception):
    pass


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    async def save(
        self, key: str, data: bytes, content_type: str = ''
    ) -> str:  # pragma: no cover
        """Persist data under key and return a reference URI."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, key: str) -> None:  # pragma: no cover
        raise NotImplementedError


_SAFE_FILENAME = re.compile(r'[^a-zA-Z0-9._\-]')


def safe_filename(name: str) -> str:
    """Return a filename with unsafe characters replaced by underscores."""
    stem = pathlib.Path(name).stem
    suffix = pathlib.Path(name).suffix
    safe_stem = _SAFE_FILENAME.sub('_', stem)
    safe_suffix = _SAFE_FILENAME.sub('_', suffix)
    return f'{safe_stem}{safe_suffix}'


class LocalStorage(StorageBackend):
    """Stores files on the local filesystem under base_path.

    Suitable for development. Replace with S3-compatible backend for production.
    """

    def __init__(self, base_path: str | pathlib.Path) -> None:
        self.base_path = pathlib.Path(base_path)

    async def save(self, key: str, data: bytes, content_type: str = '') -> str:
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def get(self, key: str) -> bytes:
        path = self.base_path / key
        if not path.exists():
            raise StorageError(f'Key not found: {key}')
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self.base_path / key
        path.unlink(missing_ok=True)


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    if _backend is None:
        raise RuntimeError('Storage backend not configured — call set_storage in startup')
    return _backend


def set_storage(backend: StorageBackend) -> None:
    global _backend
    _backend = backend


ALLOWED_CONTENT_TYPES: typing.Final[frozenset[str]] = frozenset(
    {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'audio/mpeg',
        'audio/wav',
        'audio/ogg',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
)
