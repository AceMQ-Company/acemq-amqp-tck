# Design

Decisions behind the TCK, written before it was built and kept current.

## The problem

Five libraries implement one contract. Until this kit, each proved its own
behaviour with its own tests, against its own reading of the contract — so a
library could be wrong and green. In the 48 hours before v0.1.0 six
divergences were found by reading code, every one of them in a library whose
suite passed:

| Behaviour | What diverged |
|---|---|
| a scheduled message due at a destination nothing is bound to | Python dropped it; Go and Java dead-lettered it |
| a retry hop whose publish fails | Java closed the channel when the publish threw; Ruby left the delivery unacknowledged when a rung refused it |
| a reply the caller cannot decode | Python, Go and Ruby waited out the timeout |
| a generated reply queue | Go and Ruby left a durable `.dlq` and `.parked` behind each one |
| publishes made on the user's behalf | not all mandatory and confirmed when the user's confirms were off |
| telemetry outcome of a refused publish | `failed` in some, `refused` in others |

A divergence is a failing test or it is an accident waiting to be read.

## Where it lives: a repository of its own

`AceMQ-Company/acemq-amqp-tck`, public, Apache-2.0 like the libraries.

- Not inside one library: the contract would then belong to that library, and
  a change to it would be reviewed as a change to that library.
- Not in the private workspace: the libraries' CI has to fetch it, and anyone
  porting AceMQ to a sixth language needs to read it.
- It holds the **spec** (`spec/`, numbered requirements), the **cases**
  (`cases/`, language-neutral), the **runner and checker** (`runner/tck.py`),
  the **canonical fixtures** (`fixtures/`, the byte-level contract Java
  generates) and a **GitHub Action** (`action.yml`) that runs it all.

## Execution model: library drivers, one shared runner and checker

```
                 cases/*.json
                      |
        +-------------v--------------+        management API
        |  runner/tck.py             |----------------------------+
        |  - names resources         |                            |
        |  - arranges the broker     |                     +------v------+
        |  - plays the faulty peer   |                     |  RabbitMQ   |
        |  - checks the outcome      |                     +------^------+
        +-------------+--------------+                            |
                      | JSON lines (stdin/stdout)                 | AMQP
        +-------------v--------------+                            |
        |  driver (in the library's  |----------------------------+
        |  repo, under test sources) |   through the real library
        +----------------------------+
```

- **Drivers are thin.** Each library ships a driver under its own test
  sources that maps a handful of operations (`publish`, `consume`, `schedule`,
  `request`, ...) onto its public API. It asserts nothing. See
  [driver-contract.md](driver-contract.md).
- **One checker.** Every assertion is made once, in the runner, on
  broker-observable state read through the RabbitMQ management API — queue
  contents, headers, properties, the `redelivered` flag, depths, consumer
  counts, which queues exist. Where a behaviour is only visible to the caller
  (an error raised, how fast), the driver reports a normalised outcome (`kind`
  from a closed list) and the runner times it. Five libraries cannot assert
  five ways.
- **The runner plays the misbehaving world.** Faults are injected at the
  broker, not inside the library: a reject-publish policy makes the broker
  nack a retry hop; a responder that answers with bytes that are not JSON is
  the runner itself; a destination is bound late by the runner. Nothing is
  mocked, so a case exercises the same code a production failure does.
- **Why not one driver library per language plus per-language assertions**
  (the original idea in the 06 strategy document, a Testcontainers runner in
  each language): five assertion implementations is the failure mode this kit
  exists to remove, and five YAML parsers and matchers is five more places for
  it to recur.
- **Why a long-lived driver process rather than one per case:** a JVM or a
  .NET host starting per step would make the kit minutes slower and would
  make state that must persist across steps (a consumer, a scheduler, a
  requester) impossible to express.
- **Why stdlib Python for the runner:** every CI image has a `python3`;
  nothing is installed, so the kit cannot break on a dependency.
- **Why JSON for cases, not YAML:** the runner would need a YAML parser,
  which the standard library does not have. JSON is readable enough for
  cases this size, and every language parses it without a dependency.

## Case format

One JSON file per case in `cases/`:

```json
{
  "id": "SCHED-001",
  "title": "a due message nothing is bound for yet is kept ...",
  "requirements": ["AMQP-SCHED-001", "AMQP-SCHED-002"],
  "steps": [
    {"broker": "declareExchange", "exchange": "${ns}.ex"},
    {"driver": "schedule", "delayMs": 2000, "exchange": "${ns}.ex", "routingKey": "k", "body": {"id": "s-1"}},
    {"sleep": 8000},
    {"expect": "noMessagesIn", "pattern": "\\.(dlq|parked)$"},
    {"expect": "message", "queue": "${ns}.q", "withinMs": 30000, "match": {"body": {"id": "s-1"}}}
  ]
}
```

- A step is exactly one of `driver` (an op sent to the driver; `as` records
  its outcome for a later `expect: step`), `broker` (done by the runner:
  `declareQueue`, `declareExchange`, `bind`, `policy`, `clearPolicy`,
  `publish`, `respond`), `expect` (`message`, `depth`, `consumers`, `queue`,
  `queueAbsent`, `noNewQueues`, `noMessagesIn`, `step`, `driver`, `drain`) or
  `sleep`. `drain` takes every ready message off a queue with a basic.get and
  matches `{"count", "ids"}` (body ids, sorted): exact at that instant, where
  `depth` reads a statistic that can be a stats interval old, so it is the one
  for "right after the driver returned". It consumes, so it is never polled.
- `${ns}` is a fresh namespace per run of a case (`tck.<case>.<random>`), and
  `${nsre}` the same escaped for a regular expression. Everything a case
  creates, and everything created on the broker while it ran, is deleted
  after it.
- `match` is a subset match with a few operators: `$regex`, `$type`, `$gt`,
  `$gte`, `$lt`, `$lte`, `$sameAs` (another field of the same message),
  `$absent`, `$oneOf`.
- `expect` with `withinMs` polls until it holds or the time is up — the only
  way a timing-dependent outcome is asserted.

## Versioning

- The TCK is versioned on its own (`VERSION`, tag `vX.Y.Z`). A **patch** fixes
  the runner or a case without changing what is required; a **minor** adds
  cases, requirements or driver ops; a **major** changes what an existing
  requirement means.
- A library **pins** the version it passes in exactly one place: the `uses:`
  line of its `tck` CI job, `AceMQ-Company/acemq-amqp-tck@vX.Y.Z`. The action
  is the runner at that tag, so the pin is the whole kit — cases, checker and
  broker setup — and moving it is a one-line, reviewable change.
- The workspace release preflight refuses a library release whose pin is not
  the newest TCK tag, so a library cannot ship while it has not run the
  current contract.
- The fixtures in `fixtures/` remain generated by `acemq-java-amqp`; this copy
  is the reference the workspace's fixture-drift check compares the five
  library copies against.
