# 03 — Retry

A handler failure is retried by republishing the message one attempt further
on: below the broker-wait threshold (30 s by default) after waiting in the
consumer, at or above it through a `{queue}.retry.{delay}` rung whose TTL
dead-letters back to the source. Exhausted retries go to `{queue}.dlq`;
messages that cannot be decoded go to `{queue}.parked`. The numeric contract
(schedules, jitter, the threshold, rung arguments) is pinned by
[`fixtures/contract-fixtures.json`](../fixtures/contract-fixtures.json).

### AMQP-RETRY-001 (MUST) A failed hop settles only its own delivery, by requeue

Cases: RETRY-001

When the publish that carries a retry onward (to the source queue or a rung)
fails — refused, nacked, or the publishing channel is gone — the delivery it
was for is requeued at once. No other delivery in flight on the consumer is
settled, redelivered or delayed by it.

A rung that is **missing** (the hop is returned unroutable) MAY instead be
waited out in the consumer and the message republished to the source queue,
counted on `acemq.retry.rung.missing` — the degraded path for a consumer
started without declaring its topology. Nothing is lost either way.

### AMQP-RETRY-002 (MUST) The consumer survives a failed hop

Cases: RETRY-001

The consumer stays subscribed and its channel open; messages published after
the failure are handled without a restart.

### AMQP-RETRY-003 (MUST) A hop advances the attempt

Cases: RETRY-002

The republished message carries `x-acemq-attempt` one greater than the
delivery it replaces, and every other envelope header unchanged.

### AMQP-RETRY-004 (MUST) Failure queues are named `{queue}.dlq`, `{queue}.parked`, `{queue}.retry.{delay}`

Cases: RETRY-001, RETRY-002

### AMQP-RETRY-005 (MUST) Exhausted retries are dead-lettered with the reason

Cases: RETRY-002

The message in `{queue}.dlq` carries the attempt it failed on, every
envelope and application header it arrived with, and the reason as a string
in `x-acemq-error`.
