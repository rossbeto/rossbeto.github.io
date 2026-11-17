---
title: "tenantlab: a multi-tenant Django reference app"
summary: One Django codebase serving several partner companies, each on its own database shard, with a portal embedded in their sites and a self-rolling-back deploy.
stage: active
kind: lab
repo: https://github.com/rossbeto/prj_django_tenant_lab
repo_public: false
image: assets/projects/tenantlab/poster.png
image_alt: The tenant portal signed in inside a partner's website, in an iframe
tags: [django, multi-tenancy, mysql, security, concurrency, deploy, ci]
featured: true
order: 1
---

# tenantlab: a multi-tenant Django reference app

!!! info "A personal lab"
    I built this on my own time to work through problems I find interesting. The numbers on this
    page are **test numbers** (835 tests, 97.5 % coverage on the full suite, two database
    engines), not production traffic.

**Repository:** publishing soon. Until then, every claim below names the test that proves it.

## The problem

One codebase serves several partner companies ("tenants"). Each has its own data on one of two
MySQL shards, its own branding, language and email templates, and its own website that embeds the
customer portal. The interesting parts are the ones that usually go wrong in production:

- tenant isolation that the code **enforces**, instead of hoping every query remembers it;
- a portal inside a partner's iframe that still works when browsers block third-party cookies;
- read replicas without "I just saved it and it's gone";
- a deploy that undoes itself when the new release is unhealthy.

![Demo: partner-a frames the portal, evil.test is refused, a cookieless tenant logs in with third-party cookies blocked](../assets/projects/tenantlab/demo.gif){ loading=lazy }

## What I built

- **Tenant isolation in the ORM:** every query must name its tenant; an unscoped query, `raw()`
  or a write to another shard raises before a connection opens.
- **Secure partner embedding:** per-tenant `frame-ancestors`, sessions bound to the tenant, and a
  header-session mode for browsers that block third-party cookies.
- **An API that stays correct under concurrency:** atomic lockout counters, idempotency keys
  arbitrated by a unique constraint, ETag compare-and-set, row locks for limits.
- **Read-your-writes on a delayed replica:** a sticky window after a write, or a signed token
  carrying the replication position.
- **A deploy tool with no dependencies** (Python standard library only): a byte-reproducible
  artefact, 19 deploy steps, an atomic release switch, systemd socket activation, a health gate
  and automatic rollback, all testable as a normal user.

![tlbuilder: the 19-step deploy plan and a dry-run deploy in the terminal](../assets/projects/tenantlab/tlb.gif){ loading=lazy }

## What it demonstrates

| Claim | Proof (test) |
|---|---|
| An unscoped query, `raw()` or a cross-shard write raises | `test_unscoped_queries_raise`, `test_raw_is_blocked` |
| Partner-a may frame its portal; `evil.test` may not (Chromium and Firefox) | `test_evil_cannot_frame_portal` (Playwright) |
| The portal works with third-party cookies blocked | `test_header_mode_works_with_cookies_blocked` (Playwright) |
| Lockout counters count every failure under parallel requests | `test_concurrent_failures_are_all_counted` |
| Two identical POSTs at once create exactly one row | `test_concurrent_begin_has_exactly_one_owner` |
| Two edits with the same ETag: one wins, one gets 412 | `test_concurrent_patches_with_the_same_etag_one_wins` |
| Tenant-authored templates can't run code (SSTI) | `test_ssti_and_mutation_are_blocked` |
| A read right after a write sees the write; turning the fix off reproduces the bug | `test_in_request_write_sticks_to_primary`, `test_mode_off_reproduces_the_anomaly` |
| A device limit holds under 10 concurrent threads | `test_device_limit_holds_under_concurrency` |
| A redirect no longer inherits the previous request's tenant | `test_naive_middleware_leaks_tenant_on_301` |
| Rebuilding the release gives a byte-identical file | `test_reproducible_tar` |
| A failed health check rolls the release back | `test_health_gate_failure_rolls_back` |
| The whole deploy runs as a normal user and issues exactly the reviewed commands | `test_recorded_commands_match_golden` |

Architecture rules (layers, Django-free services, app separate from the deploy tool) and the
supply chain (SHA-pinned actions, least-privilege tokens, SBOM and provenance, image scanning)
are enforced in CI on every pull request.

## Hard parts and lessons

- **Request state must live as long as the request, no longer.** A redirect that never reached a
  view inherited the previous customer's tenant. The story:
  [The 301 that leaked a tenant](../blog/posts/the-301-that-leaked-a-tenant.md).
- **A rehearsal proves the logic, not the host.** The first real deploy found three bugs that
  hundreds of tests missed, because the fakes agreed with my assumptions:
  [What my first real deploy taught my tests](../blog/posts/what-my-first-real-deploy-taught-my-tests.md).
- **Fakes must stay honest.** One contract test suite runs against both the in-memory fake and
  the real database repository. It caught a real difference: the database broke the caller's
  transaction on a duplicate key while the fake didn't. A savepoint fixed it.

## Tech

Python 3.13 · Django 5.2 LTS · Django REST Framework · MySQL 8.4 and MariaDB 11.8 (GTID
replication) · Valkey · Jinja2 (sandboxed) · gunicorn · nginx · systemd · Docker Compose ·
Playwright · pytest · mypy --strict · import-linter · uv · GitHub Actions · Trivy · SBOM and SLSA
provenance

## Links

- Repository: publishing soon
- Related posts: [The 301 that leaked a tenant](../blog/posts/the-301-that-leaked-a-tenant.md) ·
  [What my first real deploy taught my tests](../blog/posts/what-my-first-real-deploy-taught-my-tests.md)
