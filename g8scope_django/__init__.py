"""g8scope Django adapter — captures unhandled exceptions via the g8scope SDK."""

from .context import build_context
from .middleware import G8ScopeMiddleware

__version__ = "1.0.0"

default_app_config = "g8scope_django.apps.G8ScopeConfig"

__all__ = [
    "G8ScopeMiddleware",
    "build_context",
    "__version__",
]
