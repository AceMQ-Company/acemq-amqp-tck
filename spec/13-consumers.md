# 13 — Consumer groups and shutdown

### AMQP-CONSUME-001 (MUST) A consumer group of n is n consumers

Cases: CONSUME-001

A consumer group of size `n` on a queue is `n` consumers on the broker, on
that queue, each with the prefetch the caller gave — not one consumer with a
larger prefetch, not one channel's prefetch shared — so the broker spreads
deliveries across them and `n` handlers run at once. Each member is the
consumer the library builds for that queue on its own: the same topology,
the same retry policy and dead-lettering.

### AMQP-CONSUME-002 (MUST) Closing drains what is in flight

Cases: CONSUME-002

Closing a consumer, or the connection it runs on, first stops new deliveries
(`basic.cancel`), then waits — up to the library's drain timeout — for every
handler already running to finish and for its delivery to be settled, and
only then closes the channel. A message whose handler finished is
acknowledged, not handed back to the queue to be handled a second time by the
next consumer; a message that was prefetched but never handed to a handler is
returned to the queue untouched, never delivered to a handler during the
drain.
