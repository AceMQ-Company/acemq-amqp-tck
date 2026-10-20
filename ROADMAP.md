# Roadmap

What the kit does not cover yet, and what it found that is not closed.

## Pending cases — divergences not every library has closed

`cases/pending/` holds cases that pass in some libraries and fail in others.
They are kept out of the default run, so that a tagged TCK is one every
library passes, and run with `--pending`. A pending case moves into `cases/`
— and the TCK takes a new version — once all five pass it.

None at the moment. The R6 set — PARK-001, PARK-002, RETRY-004, REPLAY-002,
PUB-003, STREAM-003, IDEM-001, SLIP-001 and SLIP-002 — moved into `cases/` in
v0.3.1, once Java 0.7.17, .NET 0.7.15, Python 0.7.14, Ruby 0.7.16 and Go
0.9.11 passed them; REPLAY-001 moved in v0.3.0, RR-004 and TEL-001..003 in
v0.2.0.

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
