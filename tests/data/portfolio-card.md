# Portfolio card: tenantlab

<!-- The single source the github.io portfolio site ingests. Keep the headings stable. -->

## Title
tenantlab: a multi-tenant Django reference app

## Pitch
A Django 5.2 app serving several partner companies from one codebase, with each tenant's data on
its own MySQL shard and its portal embedded in the partner's website. It covers the parts that
usually break in production: isolation enforced by the ORM, iframes without third-party cookies,
read replicas that keep read-your-writes, and a stdlib deploy tool that rolls itself back.

## Media
- ![Demo: framing allowed for partner-a, refused for evil.test; cookieless login with third-party cookies blocked](media/demo.gif)
- ![tlbuilder: the deploy plan and a dry-run deploy](media/tlb.gif)
- Architecture and deploy diagrams: [architecture.md](architecture.md) (sections 1, 2 and 7)
- Sources to regenerate the media: [`e2e/demo/record_demo.py`](../e2e/demo/record_demo.py), [`media/tlb.tape`](media/tlb.tape)

## Highlights
- **Tenant isolation enforced in the ORM:** an unscoped query, `raw()` or a cross-shard write
  raises; proven by DB-free tests on every query path.
- **Secure partner embedding:** per-tenant CSP `frame-ancestors`, tenant-bound sessions, and a
  header-session mode that works with third-party cookies blocked (Playwright, Chromium + Firefox).
- **Correct under concurrency:** atomic lockout counters, idempotency keys arbitrated by a unique
  constraint, ETag compare-and-set, row locks for limits; each with a multi-threaded test.
- **Read-your-writes on a delayed GTID replica:** sticky window or a signed GTID token; the
  anomaly reproduced first.
- **Hermetic deploys:** a byte-reproducible artefact (wheelhouse + hashes), atomic release switch,
  systemd socket activation, health gate and automatic rollback, all testable as a normal user.

## Tech stack
Python 3.13 · Django 5.2 LTS · Django REST Framework · MySQL 8.4 / MariaDB 11.8 (GTID replication) ·
Valkey · Jinja2 (sandboxed) · gunicorn · nginx · systemd · Docker / Compose · Playwright ·
pytest · mypy --strict · import-linter · uv · GitHub Actions · Trivy · SBOM / SLSA provenance

## Links
- Repository: https://github.com/rossbeto/prj_django_tenant_lab
- README: [../README.md](../README.md)
- Architecture: [architecture.md](architecture.md)
- ADR index: [adr/README.md](adr/README.md)
- Best stories: [The 301 that leaked a tenant](interview-notes.md#2-the-301-that-leaked-a-tenant) ·
  [Deploying onto a host shared with another stack](interview-notes.md#9-deploying-onto-a-host-shared-with-another-stack)
