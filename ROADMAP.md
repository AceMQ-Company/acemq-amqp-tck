# Roadmap

What the kit does not cover yet, and what it found that is not closed.

## Pending cases — divergences not every library has closed

`cases/pending/` holds cases that pass in some libraries and fail in others.
They are kept out of the default run, so that a tagged TCK is one every
library passes, and run with `--pending`. A pending case moves into `cases/`
— and the TCK takes a new version — once all five pass it.

No divergence is pending at the moment. SLIP-008 and SLIP-009
(AMQP-SLIP-007, a hop publishes a new `x-acemq-id` with `x-acemq-causation`
the handled message's id and the correlation unchanged, in the route and
itinerary forms) are in `cases/` on `main` for the next tag. All five
libraries pass them on their `main` branches; the Java and .NET fixes are not
released yet, so the next TCK tag ships in the same release round as the Java
and .NET versions that carry them. Before those versions, the Java and .NET
hops carried the handled message's id onwards; Python, Ruby and Go already
minted a new one.

AI-001 to AI-007 (`spec/14-ai.md`, a model call behind a queue) are a
different kind of pending: they are not a divergence. They apply only to a
library with an AI adapter, and today that is `acemq-java-amqp-ai`, which
passes all seven and runs them in its CI with `pending: "true"` and
`only: ^AI-`. They stay in `cases/pending/` until a second adapter exists
(Python first, by the scope's port order), because the default run is the
one all five messaging libraries pass.

SLIP-006 and SLIP-007 (AMQP-SLIP-006, a hop keeps the
run's `x-acemq-first-seen`, in the route and itinerary forms) moved into
`cases/` in v0.3.4, once Java 0.7.20, .NET 0.7.18, Python 0.7.17, Ruby 0.7.19
and Go 0.9.14 passed them. Before those versions, the Python, Ruby and Go
pipeline hops started a new first-seen, so `acemq.pipeline.run.duration`
measured only the last hop; Java and .NET already kept it.

The M7 set — SLIP-004, SLIP-005, CLAIM-001, CLAIM-002,
OUTBOX-001, OUTBOX-002, CONSUME-001 and CONSUME-002 (claim check, outbox
relay, consumer groups, pipeline-hop headers and shutdown drain) — moved into
`cases/` in v0.3.3, once Java 0.7.19, .NET 0.7.17, Python 0.7.16, Ruby 0.7.18
and Go 0.9.13 passed them. Before those versions, every library's pipeline hop
dropped headers it did not own (application headers, or an unknown
`x-acemq-` header in Java); the Java and .NET outbox records had no headers,
Python's had no `x-acemq-origin` with a caller's envelope and Go's carried
`acemq@host`; and Java's consumer close did not wait for the running
handler, so the message was handled twice. No released driver answered
`claimCheck`, `outbox` or `consumeGroup` before them.

SLIP-003 moved in v0.3.2, once Java 0.7.18,
.NET 0.7.16, Python 0.7.15, Ruby 0.7.17 and Go 0.9.12 passed it (.NET's
pipeline step used to retry every 5s for ever with no policy). The R6 set —
PARK-001, PARK-002, RETRY-004, REPLAY-002, PUB-003, STREAM-003, IDEM-001,
SLIP-001 and SLIP-002 — moved in v0.3.1, REPLAY-001 in v0.3.0, RR-004 and
TEL-001..003 in v0.2.0.

The R6 set was written from reading the five libraries' code. Two of its
cases were decisions as much as defects, and the spec states one answer: a
replay clears `x-acemq-error` (Java used to keep it), and a failing stream
handler stops the reader (Python, Ruby and Go used to carry on).

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

1. Fold `scripts/parity.sh`'s capability list into the spec, so "does every
   library have X" and "does X behave the same" are answered in one place.
