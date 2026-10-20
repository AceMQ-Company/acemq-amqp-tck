# Roadmap

What the kit does not cover yet, and what it found that is not closed.

## Pending cases — divergences not every library has closed

`cases/pending/` holds cases that pass in some libraries and fail in others.
They are kept out of the default run, so that a tagged TCK is one every
library passes, and run with `--pending`. A pending case moves into `cases/`
— and the TCK takes a minor version — once all five pass it.

None at the moment. REPLAY-001 moved into `cases/` in v0.3.0, once Java
0.7.16, Python 0.7.13, Ruby 0.7.15, .NET 0.7.14 and Go 0.9.10 passed it;
RR-004 and TEL-001..003 moved in v0.2.0.

## Requirements without a case

| Requirement | Why not yet |
|---|---|
| AMQP-ENV-013 replay audit headers | the `replay` op exists (REPLAY-001); a case that reads a replayed message's headers is next |
| AMQP-PUB-001 mandatory flag on on-behalf publishes | the flag is not broker-observable; PUB-001/PUB-002 check its consequence (nothing lost with confirms off) instead |
| AMQP-PUB-003 unroutable user publish is an error | needs a `mandatory` argument on `publish`; Java and .NET report unroutable and nacked as one exception type, so drivers tell them apart by message text |
| AMQP-STREAM-003 retry on a stream does not append | needs a failing handler on `readStream` |

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
2. Driver ops for replay, unroutable user publishes and failing stream
   handlers, so the last requirements get cases.
3. Fold `scripts/parity.sh`'s capability list into the spec, so "does every
   library have X" and "does X behave the same" are answered in one place.
