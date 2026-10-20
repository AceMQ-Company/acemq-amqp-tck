# Roadmap

What the kit does not cover yet, and what it found that is not closed.

## Pending cases — divergences not every library has closed

`cases/pending/` holds cases that pass in some libraries and fail in others.
They are kept out of the default run, so that a tagged TCK is one every
library passes, and run with `--pending`. A pending case moves into `cases/`
— and the TCK takes a minor version — once all five pass it.

REPLAY-001 moved into `cases/` in v0.3.0, once Java 0.7.16, Python 0.7.13,
Ruby 0.7.15, .NET 0.7.14 and Go 0.9.10 passed it; RR-004 and TEL-001..003
moved in v0.2.0.

The R6 set below was written from reading the five libraries' code, not from
a run: "suspected" is what the code says each library does. None of them has
been run yet, because each needs driver work first (the `pipeline` op, or an
argument the drivers ignore today).

| Case | Asserts | Needs in the drivers | Suspected to diverge |
|---|---|---|---|
| PARK-001 | an undecodable body is parked once, unhandled, with every header it arrived with (AMQP-RETRY-006, AMQP-ENV-014) | nothing new | Python, Ruby, Go (headers rebuilt from the envelope: an unknown `x-acemq-` header is dropped) |
| PARK-002 | a park the broker refuses requeues the delivery (AMQP-RETRY-007) | nothing new | Python, Ruby (`nack(requeue=false)` when the park publish fails) |
| RETRY-004 | a consumer given no retry policy dead-letters after one attempt (AMQP-RETRY-008) | `consume` without `retry` | .NET (retries every 5s for ever), Go (republishes with attempt+1 without limit); Python, Ruby, Go also drop the unknown header |
| REPLAY-002 | replay audit headers, millisecond `acemq-replayed-at`, count incremented, attempt 1, no `x-acemq-error` (AMQP-ENV-013, AMQP-REPLAY-003) | nothing new | all five on the timestamp (Java nanosecond-capable `Instant`, Python microseconds and `+00:00`, Ruby/.NET/Go whole seconds); Java keeps `x-acemq-error` by design; Go drops the unknown header |
| PUB-003 | an unroutable user publish is `unroutable`, by default and when asked for; a nack is `nacked` (AMQP-PUB-003, AMQP-PUB-006) | `publish` `mandatory` | Python, Ruby, Go (not mandatory by default); Java and .NET pass but only by message text |
| STREAM-003 | a failing handler stops a stream reader, copies the message nowhere, appends nothing (AMQP-STREAM-003, AMQP-STREAM-004) | `readStream` `behaviour` | Python, Ruby (dead-letter to `{stream}.dlq` and carry on), Go (park to `{stream}.parked` and carry on) |
| IDEM-001 | an idempotent consumer handles an id once, keyed by `x-acemq-id`, else `message_id` (AMQP-IDEM-001, AMQP-IDEM-002) | `consume` `idempotent` | Python, Ruby (a fresh key for a message without `x-acemq-id`) |
| SLIP-001 | a foreign route is followed: position, run id and correlation (AMQP-SLIP-001, AMQP-SLIP-003) | `pipeline` op | none found; Python needs the driver to declare the topology |
| SLIP-002 | a foreign itinerary is followed to a non-step destination, `done` recorded (AMQP-SLIP-002, AMQP-SLIP-003) | `pipeline` op | none found |

Two of these are decisions as much as defects, and the spec states one answer
so that the divergence is visible: whether a replay clears `x-acemq-error`
(Java keeps it deliberately) and what a failing stream handler does by
default (stop, as Java and .NET do and the streams guide describes).

## Known limits of the cases that exist

- **A hop publish that throws** (rather than being refused). Java's channel
  closed when the retry hop's publish threw on a lost publishing channel
  (fixed in 0.7.14, covered by Java's own `RetryHopFailureIT`). A broker
  refusal does not throw in Java, and nothing reachable from the broker makes
  a default-exchange publish throw without also closing the consumer's
  connection, so RETRY-001 and RETRY-003 do not reproduce it.
- **Quorum rungs.** RETRY-003 refuses the rung hop with a reject-publish
  policy. A quorum queue admits one message into an empty queue at a limit of
  zero, so on a library whose rungs are quorum queues the case is weaker.
- **One broker version.** The action runs `rabbitmq:4-management`; a library
  can pass `image: rabbitmq:3.13-management` for its compatibility job.

## Next

1. Close the pending divergences in the libraries, move the cases into
   `cases/`, tag v0.2.0, move every pin.
2. Driver work for the R6 pending set above: the `pipeline` op, and the
   `mandatory`, `idempotent`, no-`retry` and stream `behaviour` arguments.
3. Fold `scripts/parity.sh`'s capability list into the spec, so "does every
   library have X" and "does X behave the same" are answered in one place.
