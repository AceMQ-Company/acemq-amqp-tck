# Changelog

## [Unreleased]

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
