# Test recommendations — payments-service

> Generated drafts. Tests must be reviewed before commit; mocks should align
> with enterprise testing standards.

Target coverage: **80%**. Framework: **JUnit 5** + Mockito; Testcontainers for
integration.

## Drafted unit tests

| File | Covers |
|---|---|
| `src/test/java/com/example/OrderServiceTest.java` | Happy path, validation errors, event publication |
| `src/test/java/com/example/OrderControllerTest.java` | Web layer: status codes, payload mapping |

## Recommendations

1. **Add contract tests for the event publisher.** The `OrderEventPublisher`
   has no coverage; a contract test prevents schema drift on the topic.
2. **Introduce Testcontainers** for `OrderRepository` integration tests against
   a real database engine instead of an in-memory substitute.
3. **Add idempotency tests** for `POST /orders` once the `Idempotency-Key`
   header is implemented.
4. **Negative-path coverage** for refunds (refund exceeding order total, refund
   of a non-existent order).

## Example (excerpt)

```java
@Test
void createOrder_publishesDomainEvent() {
    var request = new CreateOrderRequest("cust-123", List.of(new Item("ABC-1", 2)), "EUR");

    var created = orderService.create(request);

    assertThat(created.status()).isEqualTo(OrderStatus.PENDING_PAYMENT);
    verify(eventPublisher).publish(any(OrderCreatedEvent.class));
}
```
