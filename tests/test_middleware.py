import re

from bliptrace import Client, Config, Transport

from bliptrace_django import build_context
from bliptrace_django.middleware import BliptraceMiddleware

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class FakeTransport(Transport):
    """Records sent envelopes; no network."""

    def __init__(self):
        self.sent = []

    def send(self, endpoint, key, envelope, timeout):
        self.sent.append(
            {
                "endpoint": endpoint,
                "key": key,
                "envelope": envelope,
                "timeout": timeout,
            }
        )


class FakeUser:
    def __init__(self, id=None, is_authenticated=False):
        self.id = id
        self.is_authenticated = is_authenticated


class FakeRequest:
    """Duck-typed Django HttpRequest — no Django settings module required."""

    def __init__(self, method="GET", path="/orders", headers=None, user=None,
                 absolute_uri=None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.user = user
        self._absolute_uri = absolute_uri

    def build_absolute_uri(self):
        return self._absolute_uri


def _raise(exc):
    """Raise then return the exception with a real traceback attached."""
    try:
        raise exc
    except BaseException as e:  # noqa: BLE001
        return e


def _client_with_transport(**config_kwargs):
    t = FakeTransport()
    config = Config(sdk_name="bliptrace-django", sdk_version="1.0.0", **config_kwargs)
    return Client(config, t), t


# --- process_exception ------------------------------------------------------

def test_process_exception_builds_and_ships_a_valid_envelope():
    client, t = _client_with_transport(key="k", endpoint="http://api")
    mw = BliptraceMiddleware(get_response=lambda r: r, client=client)

    request = FakeRequest(method="POST", path="/checkout")
    mw.process_exception(request, _raise(RuntimeError("boom")))

    assert len(t.sent) == 1
    env = t.sent[0]["envelope"]
    assert env["runtime"]["name"] == "python"
    assert env["sdk"]["name"] == "bliptrace-django"
    assert env["sdk"]["version"]
    assert env["exception"]["type"] == "RuntimeError"
    assert env["exception"]["message"] == "boom"
    assert "project" not in env
    # request context made it into the envelope
    assert env["context"]["request"]["method"] == "POST"
    assert env["context"]["request"]["url"] == "/checkout"


def test_process_exception_includes_authenticated_user_id():
    client, t = _client_with_transport(key="k")
    mw = BliptraceMiddleware(get_response=None, client=client)

    request = FakeRequest(user=FakeUser(id=42, is_authenticated=True))
    mw.process_exception(request, _raise(ValueError("x")))

    assert t.sent[0]["envelope"]["context"]["user"]["id"] == "42"


def test_process_exception_returns_none_so_django_continues():
    client, _ = _client_with_transport(key="k")
    mw = BliptraceMiddleware(get_response=None, client=client)
    result = mw.process_exception(FakeRequest(), _raise(Exception("x")))
    assert result is None


# --- disabled / no key ------------------------------------------------------

def test_disabled_sends_nothing():
    client, t = _client_with_transport(key="k", enabled=False)
    mw = BliptraceMiddleware(get_response=None, client=client)
    mw.process_exception(FakeRequest(), _raise(Exception("x")))
    assert t.sent == []


def test_no_key_sends_nothing():
    client, t = _client_with_transport(key=None)
    mw = BliptraceMiddleware(get_response=None, client=client)
    mw.process_exception(FakeRequest(), _raise(Exception("x")))
    assert t.sent == []


def test_no_client_sends_nothing_and_does_not_raise():
    mw = BliptraceMiddleware(get_response=None, client=None)
    # Must not raise even though there is no client.
    mw.process_exception(FakeRequest(), _raise(Exception("x")))


# --- robustness -------------------------------------------------------------

def test_never_raises_on_weird_request():
    client, t = _client_with_transport(key="k")
    mw = BliptraceMiddleware(get_response=None, client=client)

    class WeirdRequest:
        @property
        def method(self):
            raise RuntimeError("nope")

        @property
        def headers(self):
            raise RuntimeError("nope")

        @property
        def user(self):
            raise RuntimeError("nope")

    # Must not raise; capture still happens with a minimal context.
    mw.process_exception(WeirdRequest(), _raise(Exception("x")))
    assert len(t.sent) == 1


def test_call_delegates_to_get_response():
    client, _ = _client_with_transport(key="k")
    sentinel = object()
    mw = BliptraceMiddleware(get_response=lambda r: sentinel, client=client)
    assert mw(FakeRequest()) is sentinel


# --- context builder --------------------------------------------------------

def test_context_strips_authorization_and_cookie_headers():
    request = FakeRequest(
        method="GET",
        path="/secure",
        headers={
            "Authorization": "Bearer secret-token",
            "Cookie": "sessionid=abc",
            "Content-Type": "application/json",
            "X-Custom": "ok",
        },
    )
    ctx = build_context(request)
    headers = ctx["request"]["headers"]
    assert "Authorization" not in headers
    assert "Cookie" not in headers
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Custom"] == "ok"


def test_context_yields_method_and_prefers_absolute_uri():
    request = FakeRequest(
        method="DELETE",
        path="/items/1",
        absolute_uri="https://app.example.com/items/1",
    )
    ctx = build_context(request)
    assert ctx["request"]["method"] == "DELETE"
    assert ctx["request"]["url"] == "https://app.example.com/items/1"


def test_context_falls_back_to_path_without_absolute_uri():
    request = FakeRequest(method="GET", path="/fallback", absolute_uri=None)
    ctx = build_context(request)
    assert ctx["request"]["url"] == "/fallback"


def test_context_anonymous_user_has_no_user_key():
    request = FakeRequest(user=FakeUser(is_authenticated=False))
    ctx = build_context(request)
    assert "user" not in ctx


def test_context_always_has_custom():
    ctx = build_context(FakeRequest())
    assert ctx["custom"] == {}


def test_context_never_raises_on_garbage():
    ctx = build_context(object())
    assert "custom" in ctx
