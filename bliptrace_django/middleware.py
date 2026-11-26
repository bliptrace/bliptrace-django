"""Django middleware that captures unhandled exceptions via the Bliptrace SDK.

Thin glue over the runtime ``bliptrace`` Python SDK. It builds a :class:`Client`
once from Django settings and, on each unhandled exception, enriches it with
request context and ships it. Everything is guarded — capturing must NEVER
break the host application.

The project is resolved server-side from the ingest key; it is never carried
in the payload.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from bliptrace import Client, Config

from .context import build_context

# Settings keys we accept (either nested in a ``BLIPTRACE`` dict or as
# individual ``BLIPTRACE_<KEY>`` settings) mapped to ``Config`` kwargs.
# The old ``G8SCOPE`` / ``G8SCOPE_<KEY>`` names still work (deprecated).
_PREFIXES = ("G8SCOPE", "BLIPTRACE")  # lowest precedence first
_CONFIG_KEYS = (
    "key",
    "endpoint",
    "environment",
    "release",
    "timeout",
    "max_frames",
    "max_message",
    "ignore_exceptions",
    "scrub_keys",
    "base_path",
    "enabled",
)


class BliptraceMiddleware:
    """Standard Django middleware.

    Add ``'bliptrace_django.middleware.BliptraceMiddleware'`` to ``MIDDLEWARE``.
    """

    def __init__(self, get_response: Any = None, client: Optional[Client] = None):
        self.get_response = get_response
        # Allow injecting a pre-built client (handy for tests); otherwise
        # build one from Django settings with a safe fallback.
        self.client = client if client is not None else _build_client()

    def __call__(self, request: Any) -> Any:
        # ``get_response`` is absent in some test harnesses; tolerate it.
        if self.get_response is None:
            return None
        return self.get_response(request)

    def process_exception(self, request: Any, exception: BaseException) -> None:
        """Capture an unhandled exception, then let Django handle it normally."""
        try:
            if self.client is None:
                return None
            context = build_context(request)
            self.client.capture(exception, context)
        except Exception:
            # Never break the host app from the error path.
            pass
        # Returning ``None`` lets Django continue its own exception handling.
        return None


def _build_client() -> Optional[Client]:
    """Build a :class:`Client` from Django settings, or ``None`` on failure."""
    try:
        config = Config(**_read_settings())
        return Client(config)
    except Exception:
        return None


def _read_settings() -> Dict[str, Any]:
    """Read config from Django settings.

    Accepts a ``BLIPTRACE`` dict and/or individual ``BLIPTRACE_<KEY>`` settings
    (deprecated ``G8SCOPE`` / ``G8SCOPE_<KEY>`` names are used as fallback).
    Returns kwargs suitable for :class:`bliptrace.Config`. Tolerant of a missing
    or unconfigured Django settings module.
    """
    settings = _django_settings()
    values: Dict[str, Any] = {}

    # Any BLIPTRACE name wins over any G8SCOPE name; the G8SCOPE names are
    # deprecated fallbacks (removed in the next major). Within a prefix,
    # individual <PREFIX>_<KEY> settings override the nested dict.
    for prefix in _PREFIXES:
        nested = _getattr(settings, prefix, None)
        if isinstance(nested, dict):
            for name, value in nested.items():
                key = str(name).lower()
                if key in _CONFIG_KEYS:
                    values[key] = value
        for key in _CONFIG_KEYS:
            value = _getattr(settings, prefix + "_" + key.upper(), _MISSING)
            if value is not _MISSING:
                values[key] = value

    # Tag the SDK so the platform knows the report came via the Django adapter.
    values.setdefault("sdk_name", "bliptrace-django")
    values.setdefault("sdk_version", "1.0.0")
    return values


_MISSING = object()


def _django_settings():
    try:
        from django.conf import settings  # type: ignore

        return settings
    except Exception:
        return None


def _getattr(obj: Any, name: str, default: Any) -> Any:
    if obj is None:
        return default
    try:
        return getattr(obj, name, default)
    except Exception:
        return default
