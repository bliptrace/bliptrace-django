"""Optional tests for the Django settings glue.

These only run when Django is installed; they configure a minimal in-memory
settings module so we never need a full Django project.
"""

import pytest

django = pytest.importorskip("django")

from django.conf import settings  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_django_settings():
    """Configure minimal Django settings for the duration of each test."""
    if not settings.configured:
        settings.configure(DEBUG=True)
    yield


def _set(**kwargs):
    for name, value in kwargs.items():
        setattr(settings, name, value)


def test_read_settings_from_g8scope_dict():
    from g8scope_django.middleware import _read_settings

    _set(G8SCOPE={"key": "from-dict", "endpoint": "http://x", "enabled": True})
    values = _read_settings()
    assert values["key"] == "from-dict"
    assert values["endpoint"] == "http://x"
    assert values["sdk_name"] == "g8scope-django"


def test_individual_settings_override_dict():
    from g8scope_django.middleware import _read_settings

    _set(G8SCOPE={"key": "from-dict"}, G8SCOPE_KEY="from-individual")
    values = _read_settings()
    assert values["key"] == "from-individual"


def test_build_client_from_settings_and_capture():
    from g8scope import Transport
    from g8scope_django.middleware import G8ScopeMiddleware

    class T(Transport):
        def __init__(self):
            self.sent = []

        def send(self, endpoint, key, envelope, timeout):
            self.sent.append(envelope)

    _set(G8SCOPE={"key": "k", "endpoint": "http://api"})
    # Build via settings (no injected client), then swap in a fake transport.
    mw = G8ScopeMiddleware(get_response=None)
    assert mw.client is not None
    t = T()
    mw.client.transport = t

    try:
        raise RuntimeError("settings-boom")
    except RuntimeError as e:
        mw.process_exception(object(), e)

    assert len(t.sent) == 1
    assert t.sent[0]["sdk"]["name"] == "g8scope-django"


def test_bliptrace_settings_win_over_deprecated_g8scope():
    from g8scope_django.middleware import _read_settings

    _set(
        G8SCOPE={"key": "old-dict", "release": "old-rel"},
        BLIPTRACE={"key": "new-dict"},
        G8SCOPE_ENVIRONMENT="old-env",
        BLIPTRACE_ENVIRONMENT="new-env",
        G8SCOPE_ENDPOINT="http://old",
    )
    try:
        values = _read_settings()
        assert values["key"] == "new-dict"
        assert values["environment"] == "new-env"
        # Old names still apply when the BLIPTRACE name is unset.
        assert values["endpoint"] == "http://old"
        assert values["release"] == "old-rel"
    finally:
        for name in ("BLIPTRACE", "G8SCOPE_ENVIRONMENT", "BLIPTRACE_ENVIRONMENT", "G8SCOPE_ENDPOINT"):
            delattr(settings, name)
