# API overview — payments-service

> Generated draft. Review before publishing.

Base path: `/api/v1`

| Method | Path | Summary | Auth |
|---|---|---|---|
| `POST` | `/orders` | Create an order and initiate payment | Bearer (OIDC) |
| `GET` | `/orders/{id}` | Retrieve an order by id | Bearer (OIDC) |
| `GET` | `/orders` | List orders (paginated) | Bearer (OIDC) |
| `POST` | `/orders/{id}/refund` | Issue a refund for an order | Bearer (OIDC) |

## `POST /orders`

Request:

```json
{
  "customerId": "cust-123",
  "items": [{ "sku": "ABC-1", "quantity": 2 }],
  "currency": "EUR"
}
```

Response `201 Created`:

```json
{
  "id": "ord-9f2c",
  "status": "PENDING_PAYMENT",
  "total": "49.98",
  "currency": "EUR"
}
```

Errors: `400` (validation), `401` (unauthenticated), `409` (duplicate order).

## Notes

- All endpoints require a valid OIDC bearer token.
- Monetary amounts are serialized as strings to avoid floating-point error.
- Idempotency is recommended for `POST /orders` via an `Idempotency-Key` header
  (not yet implemented — see `test-recommendations.md`).
