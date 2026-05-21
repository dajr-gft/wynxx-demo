# Architecture summary — payments-service

> Generated draft. Review before publishing.

## Overview

`payments-service` is a stateless Spring Boot 3.x application (Java 17, Maven)
exposing a REST API for order and payment processing. It follows a conventional
layered architecture and has no local-disk dependencies, making it a strong
candidate for containerization.

## Components

| Layer | Responsibility | Key types |
|---|---|---|
| Web | HTTP endpoints, request validation | `OrderController` |
| Service | Business logic, orchestration | `OrderService` |
| Persistence | Data access (JPA) | `OrderRepository` |
| Messaging | Domain event publication | `OrderEventPublisher` |

## Runtime view

```
Client ──HTTP──> OrderController ──> OrderService ──> OrderRepository ──> DB
                                          │
                                          └──> OrderEventPublisher ──> topic
```

## Observations

- **Stateless** — no session affinity required; horizontally scalable.
- **Externalizable config** — currently reads datasource credentials from
  `application.properties` (see risks below).
- **Test gaps** — service and web layers have sparse coverage.

## Risks

| Severity | Finding | Recommendation |
|---|---|---|
| High | Datasource credentials in `application.properties` | Move to Secret Manager / injected env vars |
| Medium | Incomplete unit test coverage | See `test-recommendations.md` |

## Recommended next steps

1. Resolve the secret-management finding.
2. Add the recommended tests.
3. Proceed with the modernization plan in `modernization-assessment.md`.
