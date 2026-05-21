# Modernization assessment — payments-service

> Generated draft. Review before publishing.

## Current state

Monolithic Spring Boot service deployed on a VM with a co-located relational
database. Configuration (including datasource credentials) is read from
`application.properties`. Deployment is manual.

## Target architecture

Containerized service on **Cloud Run** with a managed **Cloud SQL** instance and
**Secret Manager** for credentials. CI/CD via Cloud Build. Egress and tool calls
governed by **Agent Gateway** where applicable.

```
            ┌─────────────┐      ┌──────────────┐
 Client ──> │  Cloud Run  │ ───> │  Cloud SQL   │
            │ payments-svc│      └──────────────┘
            └──────┬──────┘
                   └──> Secret Manager (datasource credentials)
```

## Findings

| Severity | Finding |
|---|---|
| Info | Stateless workload — no session affinity; horizontally scalable |
| High | Embedded credentials must move to Secret Manager before migration |

## Risks

- **Embedded credentials** (High) — remediate first; blocks a clean migration.
- **No automated tests gating deploys** (Medium) — pair migration with the test
  recommendations to avoid regressions.

## Migration phases

| Phase | Objective | Effort |
|---|---|---|
| Containerize | Produce a reproducible image | S |
| Externalize state | Migrate the database to Cloud SQL | M |
| Deploy | Ship to Cloud Run with CI/CD | M |

**Estimated effort:** 4–6 person-weeks.

## Recommendation

Proceed with a phased migration to Cloud Run; address secret management first.
See `migration-plan-gcp.md` for the step-by-step plan.
