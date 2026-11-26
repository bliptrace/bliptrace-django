# bliptrace-django

Django adapter for the [Bliptrace](https://bliptrace.com) error-capture and
observability platform. A **thin** layer over the runtime
[`bliptrace` Python SDK](../bliptrace-python) — it adds Django middleware that
captures unhandled exceptions, enriches them with request context, and ships
them to your Bliptrace ingest endpoint.

It is built to **never break the host application**: every code path on the
error route is guarded, and a slow or unreachable ingest endpoint can never
slow down or crash your Django app.

## Installation

This adapter depends on the runtime `bliptrace` Python SDK. While the SDK is
unpublished, install it editable alongside this package:

```bash
python3 -m pip install --user -e ../bliptrace-python
python3 -m pip install --user -e .
```

(Once both packages are published, `pip install bliptrace-django` will pull
`bliptrace` automatically.)

## Configuration

Add the middleware to your Django `settings.py`. Place it high in the stack so
it sees exceptions raised by views and inner middleware:

```python
MIDDLEWARE = [
    # ...
    "bliptrace_django.middleware.BliptraceMiddleware",
]
```

Then configure Bliptrace. Either a single `BLIPTRACE` dict:

```python
BLIPTRACE = {
    "key": "your-ingest-key",
    "endpoint": "https://ingest.bliptrace.com",
    "environment": "production",
    # optional: "release", "timeout", "max_frames", "max_message",
    #           "ignore_exceptions", "scrub_keys", "base_path", "enabled"
}
```

...or individual settings (these override the dict):

```python
BLIPTRACE_KEY = "your-ingest-key"
BLIPTRACE_ENDPOINT = "https://ingest.bliptrace.com"
BLIPTRACE_ENVIRONMENT = "production"
```

> **Deprecated:** the old `G8SCOPE` dict and `G8SCOPE_*` settings are still
> read as a fallback when no `BLIPTRACE` setting provides the value. They will be removed
> in the next major version.

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
python3 -m pip install --user -e ../bliptrace-python
python3 -m pip install --user pytest
python3 -m pytest -q
```

The settings-glue tests additionally exercise Django if it is installed
(`python3 -m pip install --user django`); they are skipped otherwise.

## Licence

MIT © Developers Hub Sdn Bhd. British spelling throughout.
