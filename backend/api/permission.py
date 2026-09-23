"""Public access marker for the hackathon's unauthenticated MVP routes."""


class NoPermsRequired:
    async def __call__(self) -> None:
        return None
