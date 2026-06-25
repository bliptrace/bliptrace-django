"""Optional Django ``AppConfig`` for autodiscovery / nicer admin display."""

from __future__ import annotations

try:
    from django.apps import AppConfig  # type: ignore
except Exception:  # pragma: no cover - Django not installed
    AppConfig = object  # type: ignore


class G8ScopeConfig(AppConfig):  # type: ignore[misc, valid-type]
    """App config for the g8scope Django adapter."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "g8scope_django"
    verbose_name = "g8scope"
