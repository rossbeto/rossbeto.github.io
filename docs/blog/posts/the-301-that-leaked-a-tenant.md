---
date: 2026-11-17
slug: the-301-that-leaked-a-tenant
title: The 301 that leaked a tenant
description: A missing trailing slash made a multi-tenant Django app think a request belonged to the previous customer. How I reproduced it in a test, then fixed it.
authors: [lam]
categories: [Django]
tags: [multi-tenancy, middleware, contextvars, testing]
---

# The 301 that leaked a tenant

In a multi-tenant app, one server answers many customers ("tenants"), and every request must know
which one it belongs to. I built a small lab app like that, and wrote a test that sends two
requests: one for customer A, then one for customer B, with a missing slash at the end of the
URL. The second request came back tagged as **customer A**. Nothing crashed and the page
looked fine. This post shows why it happens, the test that proves it, and the small fix.

<!-- more -->

## The setup

Each URL names the tenant: `/portal/partner-a/…`, `/portal/partner-b/…`. A common way to make
"the current tenant" available everywhere (logging, templates, error pages) is a middleware that
reads the tenant from the URL in `process_view` and stores it in a request-wide variable:

```python
class NaiveContextMiddleware:
    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, args, kwargs):
        slug = kwargs.get("tenant_slug")
        tenant = tenant_service().get_active(slug) if slug else None
        _current.set(RequestContext(tenant_slug=tenant.slug if tenant else None, ...))
        # set here, never reset
```

It looks reasonable, and it works for every request that reaches a view.

## How it showed up

Django calls `process_view` only **after the URL has been resolved**. Some requests never get
that far. With `APPEND_SLASH` (the default), a request for `/portal/partner-b/ping` (no
trailing slash) doesn't match any URL. Django raises a 404, and `CommonMiddleware` turns it into
a **301 redirect** to `/portal/partner-b/ping/`. No view runs, so `process_view` never runs.

So nothing set the tenant for this request. But nothing *cleared* it either. Under a threaded
WSGI server (gunicorn with `gthread`, for example), worker threads are reused, and a context
variable set by the previous request on that thread is still there. The 301 for partner-b runs
with **partner-a's context**.

The redirect itself is harmless. The problem is everything else that runs during that request
and asks "which tenant is this?": the access log line, an error report, a branded error page.
And if anything ever used that value to choose a database, it would read the wrong customer's
data.

The same gap opens for every response that a middleware returns early: an HTTPS redirect, a
`DisallowedHost` 400, a rate-limit 429. A trailing slash is just the easiest one to trigger.

## Reproduce it first

Before fixing anything, I wanted a test that fails for the right reason. Two test-only
middlewares make the bug visible:

- the naive middleware above, at the bottom of the chain;
- a **probe** at the top of the chain, which records what the context says when each response
  goes out.

```python
def _leak_scenario() -> list[str | None]:
    RECORDED.clear()
    client = Client()
    first = client.get("/portal/partner-a/ping/")
    assert first.status_code == 200
    second = client.get("/portal/partner-b/ping")  # no slash: 404 -> APPEND_SLASH 301
    assert second.status_code == 301
    return list(RECORDED)


def test_naive_middleware_leaks_tenant_on_301(settings) -> None:
    settings.MIDDLEWARE = [PROBE, *BASE_MIDDLEWARE, NAIVE]
    recorded = _in_fresh_context(_leak_scenario)
    # Request 2 never reached process_view (URL didn't resolve), yet it "belongs" to partner-a:
    assert recorded == ["partner-a", "partner-a"]
```

The test asserts the **bug**: it passes only while the leak exists. It documents the failure mode
in code, and it proves the probe can see a leak at all. A test that can't fail proves nothing.

One detail matters here: the test deliberately leaks a value, so it must not leak it into the
*next* test. `_in_fresh_context` runs the scenario inside an empty `contextvars.Context`:

```python
def _in_fresh_context(fn):
    """Run in an empty contextvars.Context, so a deliberate leak can't escape this test."""
    return contextvars.Context().run(fn)
```

## Root cause

The lifetime of the context was tied to the wrong event. "A view is about to run" is not the
same as "a request started". Anything set on the first and cleaned up on neither will outlive
its request.

`ContextVar` doesn't fix this on its own. It makes the same code correct under threads, asyncio
tasks and greenlets, but a value you `set()` stays set until you remove it.

## The fix

One middleware owns the context's whole lifetime, and it sits **first** in `MIDDLEWARE`, so it
wraps every other middleware, including the ones that return early:

```python
@contextmanager
def bind(ctx: RequestContext) -> Iterator[RequestContext]:
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


class RequestContextMiddleware:
    def __call__(self, request):
        ctx = RequestContext(request_id=..., method=request.method, path=request.path)
        with bind(ctx):
            return self.get_response(request)
```

Every request starts with a fresh context (tenant: none). The tenant middleware later fills in
the tenant if the URL resolves. Whatever happens below, `finally` puts the previous value back.

Why `reset(token)` and not `set(None)`? `reset` restores exactly what was there before, so it
nests correctly, for example when a test or a management command has already bound a context.
`set(None)` would wipe the outer value.

## The test that keeps it fixed

Same scenario, real middleware stack:

```python
def test_context_middleware_does_not_leak_on_301(settings) -> None:
    settings.MIDDLEWARE = [REAL, PROBE, *BASE_MIDDLEWARE, TENANT]
    recorded = _in_fresh_context(_leak_scenario)
    assert recorded == ["partner-a", None]
```

The 301 now runs with no tenant, which is the truth: the URL never resolved to one.

Two more tests guard the same idea from other angles:

- **Concurrency:** 51 requests across 3 tenants on 8 threads; every response reports its own
  tenant and a unique request id.
- **No state on middleware instances:** Django builds each middleware once and shares it
  across threads, so `self.tenant = …` during a request is a race. The test snapshots
  `vars()` of every middleware in the chain, sends two dozen requests (valid, unknown tenant,
  missing slash), and checks nothing changed.

## One design rule that came out of it

In the lab, **services never read this context**. It belongs to the web and logging layers. A
service receives the tenant as a parameter, which is more typing but keeps it callable from
commands, tests and background jobs, where there is no request at all. A contract in CI
(import-linter) keeps service code from importing the context module.

## Lesson

Tie request state to the request's lifetime: set it in the outermost middleware and reset it in
`finally`. And reproduce a bug as a passing "the bug exists" test before you fix it.

---

*The code and tests are part of my [tenantlab](../../projects/tenantlab.md) lab.*
