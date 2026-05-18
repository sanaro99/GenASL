"""FakeProvider — deterministic stub for tests and offline demos."""

from __future__ import annotations

from typing import Callable


class FakeProvider:
    """Implements :class:`GlossProvider` with a canned, scripted, or callable response.

    Parameters
    ----------
    canned :
        - ``str``: returned verbatim from every ``chat()`` call.
        - ``list[str]``: returned in order; the last entry is reused after exhaustion.
        - ``Callable[[str, str], str]``: invoked with ``(system, user)`` per call.
    model :
        Reported as :attr:`model` — surfaces in render-plan metadata.
    raises :
        If provided, every ``chat()`` call raises this exception instead of returning.
    """

    name = "fake"

    def __init__(
        self,
        canned: str | list[str] | Callable[[str, str], str] = "",
        *,
        model: str = "fake",
        raises: Exception | None = None,
    ) -> None:
        self.model = model
        self._canned = canned
        self._raises = raises
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
        self._call_count += 1
        if self._raises is not None:
            raise self._raises
        if callable(self._canned):
            return self._canned(system, user)
        if isinstance(self._canned, list):
            idx = min(self._call_count - 1, len(self._canned) - 1)
            return self._canned[idx]
        return str(self._canned)
