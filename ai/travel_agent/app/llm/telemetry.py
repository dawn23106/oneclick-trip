from __future__ import annotations

from contextvars import ContextVar, Token


_fallbacks: ContextVar[list[dict[str, str]] | None] = ContextVar(
    "llm_fallbacks",
    default=None,
)


def begin_fallback_collection() -> Token:
    """Start an isolated fallback collection for one Agent run."""
    return _fallbacks.set([])


def record_fallback(stage: str, error: Exception) -> None:
    current = _fallbacks.get()
    if current is None:
        return
    current.append(
        {
            "component": stage,
            "mode": "rules_fallback",
            "reason": type(error).__name__,
        }
    )


def fallback_snapshot() -> list[dict[str, str]]:
    return list(_fallbacks.get() or [])


def end_fallback_collection(token: Token) -> None:
    _fallbacks.reset(token)
