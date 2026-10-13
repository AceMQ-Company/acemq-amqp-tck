# Changelog

## [Unreleased]

## [0.1.0] - 2026-10-13

The first version: the specification, a runner with one shared checker, and
the first slice of cases, passing in all five libraries.

- `spec/`: envelope, publishing, retry, scheduler, request/reply, streams and
  telemetry requirements.
- Cases: the envelope a publish puts on the wire, with nothing supplied and
  with everything supplied (ENV-001, ENV-002); a scheduled message due at a
  destination nothing is bound to yet (SCHED-001); a request answered, and one
  answered with a reply the caller cannot decode, neither leaving dead-letter
  queues behind (RR-001, RR-002); a retry hop the broker refuses (RETRY-001).
- `action.yml`: runs the kit in a library's CI at a pinned version.
- `fixtures/`: the reference copy of the cross-language fixtures.
