"""Build envelope context from a Django ``HttpRequest`` (or duck-typed) object.

Kept deliberately framework-light so it is testable without a configured
Django settings module — anything that walks like an ``HttpRequest`` works.
Sensitive headers (authorisation, cookie) are never forwarded; the project
is resolved server-side from the ingest key, never carried in the payload.
"""

from __future__ import annotations

from typing import Any, Dict

# Header names we never forward (lower-cased, hyphenated).
_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "set-cookie"})


def build_context(request: Any) -> Dict[str, Any]:
    """Build the ``context`` dict for the envelope from a request-like object.

    Tolerant of missing attributes and odd values — never raises.
    """
    try:
        ctx: Dict[str, Any] = {
            "request": _request_context(request),
            "custom": {},
        }
        user = _user_context(request)
        if user is not None:
            ctx["user"] = user
        return ctx
    except Exception:
        # Context enrichment must never break capture.
        return {"custom": {}}


def _request_context(request: Any) -> Dict[str, Any]:
    return {
        "method": _method(request),
        "url": _url(request),
        "headers": _headers(request),
    }


def _method(request: Any) -> str:
    try:
        return str(getattr(request, "method", "") or "")
    except Exception:
        return ""


def _url(request: Any) -> str:
    """Prefer the absolute URI, fall back to the path, then empty."""
    try:
        builder = getattr(request, "build_absolute_uri", None)
        if callable(builder):
            url = builder()
            if url:
                return str(url)
    except Exception:
        pass
    try:
        return str(getattr(request, "path", "") or "")
    except Exception:
        return ""


def _headers(request: Any) -> Dict[str, str]:
    """Collect headers, dropping sensitive ones (authorisation, cookie)."""
    out: Dict[str, str] = {}
    try:
        raw = getattr(request, "headers", None)
        items = None
        if raw is not None and hasattr(raw, "items"):
            items = raw.items()
        if items is None:
            return out
        for name, value in items:
            try:
                key = str(name)
                if key.lower() in _SENSITIVE_HEADERS:
                    continue
                out[key] = str(value)
            except Exception:
                continue
    except Exception:
        return {}
    return out


def _user_context(request: Any):
    """Return ``{"id": ...}`` for an authenticated user, else ``None``."""
    try:
        user = getattr(request, "user", None)
        if user is None:
            return None
        is_auth = getattr(user, "is_authenticated", False)
        # ``is_authenticated`` may be a property/bool; treat truthiness.
        if not is_auth:
            return None
        user_id = getattr(user, "id", None)
        if user_id is None:
            user_id = getattr(user, "pk", None)
        if user_id is None:
            return None
        return {"id": str(user_id)}
    except Exception:
        return None
