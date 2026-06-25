# g8scope-django

Django adapter for the [g8scope](https://scope.g8suite.com) error-capture and
observability platform. A **thin** layer over the runtime
[`g8scope` Python SDK](../g8scope-python) — it adds Django middleware that
captures unhandled exceptions, enriches them with request context, and ships
them to your g8scope ingest endpoint.

It is built to **never break the host application**: every code path on the
error route is guarded, and a slow or unreachable ingest endpoint can never
slow down or crash your Django app.

## Installation

This adapter depends on the runtime `g8scope` Python SDK. While the SDK is
unpublished, install it editable alongside this package:

```bash
python3 -m pip install --user -e ../g8scope-python
python3 -m pip install --user -e .
```

(Once both packages are published, `pip install g8scope-django` will pull
`g8scope` automatically.)

## Configuration

Add the middleware to your Django `settings.py`. Place it high in the stack so
it sees exceptions raised by views and inner middleware:

```python
MIDDLEWARE = [
    # ...
    "g8scope_django.middleware.G8ScopeMiddleware",
]
```

Then configure g8scope. Either a single `G8SCOPE` dict:

```python
G8SCOPE = {
    "key": "your-ingest-key",
    "endpoint": "https://ingest.scope.g8suite.com",
    "environment": "production",
    # optional: "release", "timeout", "max_frames", "max_message",
    #           "ignore_exceptions", "scrub_keys", "base_path", "enabled"
}
```

...or individual settings (these override the dict):

```python
G8SCOPE_KEY = "your-ingest-key"
G8SCOPE_ENDPOINT = "https://ingest.scope.g8suite.com"
G8SCOPE_ENVIRONMENT = "production"
```

If no key is configured, or `enabled` is `False`, the middleware quietly
captures nothing.

> **The project is resolved server-side from the ingest key.** It is never
> placed in the payload — this is anti-spoofing by design.

## What gets captured

For each unhandled exception, the adapter builds an envelope (via the SDK)
containing the exception type, message, normalised stack frames, runtime
details, and a `context` block:

- `request` — `method`, `url` (absolute URI, falling back to the path), and
  `headers` with **`Authorization`, `Cookie` and `Set-Cookie` stripped**.
- `user` — the authenticated user's id, when present.
- `custom` — reserved for your own enrichment.

Sensitive values are scrubbed by the SDK before anything is stored or sent.

## Testing

The adapter is testable without a configured Django project — the middleware
is a plain callable class and the context builder accepts duck-typed request
objects.

```bash
python3 -m pip install --user -e ../g8scope-python
python3 -m pip install --user pytest
python3 -m pytest -q
```

The settings-glue tests additionally exercise Django if it is installed
(`python3 -m pip install --user django`); they are skipped otherwise.

## Licence

MIT © Developers Hub Sdn Bhd. British spelling throughout.
