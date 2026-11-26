"""Bliptrace Django adapter — captures unhandled exceptions via the Bliptrace SDK."""

from .context import build_context
from .middleware import BliptraceMiddleware

__version__ = "1.0.0"

default_app_config = "bliptrace_django.apps.BliptraceConfig"

__all__ = [
    "BliptraceMiddleware",
    "build_context",
    "__version__",
]
