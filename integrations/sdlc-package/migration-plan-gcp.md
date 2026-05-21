# Migration plan — payments-service → Google Cloud

> Generated draft. Review before publishing.

A phased plan derived from `modernization-assessment.md`. Each phase is
independently shippable and reversible.

## Phase 0 — Remediate secrets (blocker)

- [ ] Move datasource credentials out of `application.properties`.
- [ ] Store them in **Secret Manager**; inject at runtime via env vars.
- [ ] Rotate the exposed credentials.

## Phase 1 — Containerize (effort: S)

- [ ] Add a multi-stage, rootless `Dockerfile`.
- [ ] Externalize all configuration to environment variables.
- [ ] Verify the image builds reproducibly and runs locally.

## Phase 2 — Externalize state (effort: M)

- [ ] Provision **Cloud SQL** (PostgreSQL) with private IP.
- [ ] Migrate schema and data; validate with the integration tests.
- [ ] Connect via the Cloud SQL connector; least-privilege DB user.

## Phase 3 — Deploy to Cloud Run (effort: M)

- [ ] Create a dedicated service account (least privilege).
- [ ] Deploy with `--no-allow-unauthenticated`.
- [ ] Wire **Cloud Build** CI/CD on the main branch.
- [ ] Enable **Cloud SQL** connection and **Secret Manager** access.
- [ ] Add **OpenTelemetry** export and confirm traces in Cloud Trace.

## Phase 4 — Validate and cut over

- [ ] Run load and resilience tests against the Cloud Run service.
- [ ] Shift traffic gradually (revision-based splitting).
- [ ] Decommission the VM after a soak period.

## Rollback

Each phase is reversible: keep the VM deployment live until Phase 4 cutover
completes and the soak period passes.
