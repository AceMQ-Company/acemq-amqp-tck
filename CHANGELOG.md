# Changelog

## [Unreleased]

## [0.3.3] - 2026-10-22

### Added

- Cases for claim check, outbox relay, consumer groups, pipeline-hop headers
  and shutdown drain, in the default run (38 cases): SLIP-004, SLIP-005,
  CLAIM-001, CLAIM-002, OUTBOX-001, OUTBOX-002, CONSUME-001 and CONSUME-002.
  Every library passes them: Java 0.7.19, .NET 0.7.17, Python 0.7.16, Ruby
  0.7.18 and Go 0.9.13. `spec/` has no "(pending)" markers.
- Spec: AMQP-SLIP-005 (a hop carries the headers it does not own),
  `11-claim-check.md` (AMQP-CLAIM-001 framing, AMQP-CLAIM-002 filesystem
  store), `12-outbox.md` (AMQP-OUTBOX-001 a relayed message is the recorded
  one, AMQP-OUTBOX-002 a record the broker did not take stays) and
  `13-consumers.md` (AMQP-CONSUME-001 a group of n is n consumers,
  AMQP-CONSUME-002 closing drains what is in flight).
- Driver ops `claimCheck`, `outbox` and `consumeGroup`; `end` may be called as
  a step. See docs/driver-contract.md.
- Runner: `${tmp}` (a directory per case), `broker: storeClaim`, `publish`
  with `claimKey`, `expect: claimCheck` and the `$size` operator.

## [0.3.2] - 2026-10-21

### Added

- SLIP-003 is in the default run (30 cases). Every library passes it: Java
  0.7.18, .NET 0.7.16, Python 0.7.15, Ruby 0.7.17 and Go 0.9.12. `spec/` drops
  its "(pending)" markers.
- Spec: AMQP-SLIP-004 (a pipeline step whose own handler fails, in a pipeline
  with no retry policy, is attempted once and dead-lettered to
  `{pipeline}.{step}.dlq` with every header kept: AMQP-RETRY-008 for pipeline
  steps).
- SLIP-003 (`cases/slip-003-failing-step-no-policy-one-attempt.json`). .NET
  failed it before 0.7.16: its pipeline step retried every 5s for ever when no
  policy was configured.
- Driver op `pipeline` takes an optional `behaviour`, a map from step name to
  `consume`'s behaviour (`failFirst`, `sleepMs`); see docs/driver-contract.md.

### Fixed

- A management API call that drops its connection or times out (`URLError`,
  `RemoteDisconnected`) now fails the case it happened in. It used to escape
  as a traceback that ended the whole run with exit 1 and no FAIL line, as one
  Java run did at SCHED-001 on 2026-10-20. GET and DELETE are tried three
  times first, and clean-up no longer replaces a case's outcome when it cannot
  list what the case left.

## [0.3.1] - 2026-10-20

- PARK-001, PARK-002, RETRY-004, REPLAY-002, PUB-003, STREAM-003, IDEM-001,
  SLIP-001 and SLIP-002 are in the default run (29 cases). Every library
  passes them: Java 0.7.17, .NET 0.7.15, Python 0.7.14, Ruby 0.7.16 and Go
  0.9.11. `spec/` drops their "(pending)" markers.
- Spec: AMQP-ENV-014 (an unknown `x-acemq-` header survives every on-behalf
  republish), AMQP-PUB-006 (a user publish is mandatory unless the caller opts
  out), AMQP-RETRY-006..008 (an undecodable body is parked once and unchanged;
  a refused park loses nothing; no retry policy means one attempt),
  AMQP-STREAM-004 (a failing handler stops a stream reader),
  AMQP-REPLAY-003 (a replay restarts the attempt and clears the error),
  `spec/09-idempotency.md` (AMQP-IDEM-001..002) and
  `spec/10-routing-slip.md` (AMQP-SLIP-001..003). AMQP-PUB-003 adds that the
  unroutable/nacked distinction should be part of the API (a SHOULD).
- AMQP-ENV-013, AMQP-PUB-003 and AMQP-STREAM-003 now have cases.
- Driver op `pipeline` (`name`, `steps`, `handle` -> `{}`); arguments
  `publish.mandatory`, `consume.idempotent`, `readStream.behaviour`, and
  `consume` without `retry` (no retry policy). See docs/driver-contract.md.
- Runner: matcher operator `$json` (a string that parses as JSON matching the
  pattern), for `acemq-routing-slip`.

## [0.3.0] - 2026-10-20

- `spec/08-replay.md`: AMQP-REPLAY-001 (a filtered replay returns only once
  every message it passed over is back on its queue) and AMQP-REPLAY-002 (a
  matched message is replayed exactly once).
- REPLAY-001 (`cases/replay-001-filter-skipped-back-before-return.json`) is
  in the default run (20 cases). Every library passes it: Java 0.7.16, Python
  0.7.13, Ruby 0.7.15, .NET 0.7.14 and Go 0.9.10 — each returns from a
  filtered replay only once the passed-over messages are back on the queue.
- `spec/`: the "(pending)" markers left on RR-004 and TEL-001..003 after they
  moved into the default run in 0.2.0 are gone.
- Driver op `replay` (`from`, `queue`, `ids` -> `{"replayed"}`); see
  docs/driver-contract.md.
- Runner: `expect: drain`, an exact read of a queue's ready messages
  (`{"count", "ids"}`) for checks made right after a driver step.

## [0.2.0] - 2026-10-13

- RR-004, TEL-001, TEL-002 and TEL-003 move from `cases/pending/` into the
  default run (19 cases). Every library passes them: Java 0.7.15 (responder
  failure in `acemq-error`; a publish into a blocked broker refused at once),
  Python 0.7.12 and Go 0.9.9 (the first publish after a memory alarm bounded
  instead of hanging; Go also writes `acemq.consume.attempts`), Ruby 0.7.14
  (`acemq.publish.duration`, `routing.key` and `message.type` tags), .NET
  0.7.13 (responder failure in `acemq-error`).

## [0.1.0] - 2026-10-13

The first version: the specification, a runner with one shared checker, and
the first slice of cases, passing in all five libraries.

- `spec/`: envelope, publishing, retry, scheduler, request/reply, streams and
  telemetry requirements.
- Cases (15): the envelope with nothing supplied, everything supplied and an
  empty routing key (ENV-001..003); a retry hop the broker refuses, back onto
  the source queue and into a rung, and a message that exhausts its retries
  (RETRY-001..003); a request answered, answered undecodably, and unanswered,
  none leaving dead-letter queues behind (RR-001..003); a scheduled message
  due at a destination nothing is bound to yet, and one never delivered early
  (SCHED-001..002); both on-behalf cases again with the user's confirms off
  (PUB-001..002); a stream reader resuming after its connection is cut, and
  the `1h` retention spelling (STREAM-001..002).
- Pending (`cases/pending/`, run with `--pending`): RR-004, TEL-001..003 —
  divergences not every library has closed; see ROADMAP.md.
- `action.yml`: runs the kit in a library's CI at a pinned version.
- `fixtures/`: the reference copy of the cross-language fixtures.
