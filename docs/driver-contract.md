# The driver contract

A driver is a small program in a library's own repository, under its test
sources, that performs TCK operations through that library's public API. It
decides nothing and asserts nothing; the runner does both.

## Process

- The runner starts the driver once per run with a shell command
  (`--driver "..."`), with `ACEMQ_TCK_AMQP_URL` in its environment.
- The runner writes one JSON object per line to the driver's **stdin**; the
  driver answers each with one JSON object per line on its **stdout**, in
  order, before reading the next.
- Anything else the driver or its library prints goes to **stderr**. A stdout
  line that is not JSON is passed through to the log and otherwise ignored, so
  a library that logs to stdout does not break the protocol — but it should not.
- The driver exits when stdin closes.

## Messages

Request: `{"id": 7, "op": "publish", ...arguments}`

Answer, success: `{"id": 7, "ok": true, "result": {...}}`

Answer, failure: `{"id": 7, "ok": false, "error": {"kind": "decode", "message": "...", "type": "FatalError"}}`

`kind` is one of the words below. `message` and `type` (the exception or error
type's name) are for people reading the log, never matched by a case.

| kind | when |
|---|---|
| `decode` | the library's codec could not read a body |
| `timeout` | a request/reply call got no reply in time |
| `unroutable` | the broker returned a mandatory publish |
| `nacked` | the broker nacked a publish (it reached the broker, which would not keep it) |
| `paused` | the library declined to send because the broker is blocking publishers (back pressure); nothing was written |
| `responder` | a request/reply responder reported a failure |
| `unsupported` | the op or an argument is not implemented by this driver |
| `other` | anything else |

## Operations

Every driver implements every operation below. An op the driver does not list
in `hello` fails every case that uses it.

| op | arguments | result | what it does |
|---|---|---|---|
| `hello` | — | `{"library", "version", "ops": [...]}` | the library's name and version as the library reports it; the ops implemented |
| `begin` | `case`, `clientName`, `confirms`? | `{}` | close whatever the previous case left; open a fresh connection whose origin service is `clientName`, so `x-acemq-origin` is `{clientName}@{host}`. `confirms: false` turns publisher confirms off for the user's own publishes where the library has such a switch; a library that always confirms ignores it |
| `end` | — | `{}` | close everything this case opened: consumers, schedulers, requesters, the connection. Idempotent: called again after a case's own `end` step |
| `publish` | `exchange`, `routingKey`, `body`, `envelope`?, `mandatory`? | `{"messageId"}` | publish `body` (a JSON value) with the library's JSON codec and default publish settings. `envelope` may carry `id`, `type`, `version`, `correlationId`, `causationId`, `headers`; any field absent means "let the library decide". `mandatory` absent means the library's default; `true` and `false` set it explicitly (see below). Failure kinds: `unroutable`, `nacked`, `paused` |
| `consume` | `queue`, `handle`, `prefetch`, `retry: {maxAttempts, delayMs}`?, `behaviour: {failFirst: {id: n}, sleepMs}`, `idempotent`? | `{}` | declare `queue` the way the library's own topology declares a consumed queue with that retry policy (source queue, dead-letter and parked queues, rungs), then consume it with a fixed-delay retry policy. **`retry` absent** means no retry policy at all: the consumer exactly as the library builds it when the caller configures none — not a driver default such as three attempts. The handler reads `body.id`, counts the delivery, sleeps `sleepMs`, and fails (with the library's ordinary retryable failure) for the first `n` deliveries of an id named in `failFirst`. **`idempotent: true`** makes the consumer idempotent with the library's in-memory idempotency store and its default key and retention; the count is taken inside the idempotent wrapper, so a duplicate the library suppresses is not counted |
| `handled` | `handle` | `{"counts": {id: n}, "redelivered": {id: n}, "order": [id, ...]}` | how many times the handler has been called for each id, how many of those deliveries carried the AMQP `redelivered` flag (ids with none are left out), and every id in the order it arrived |
| `schedule` | `delayMs`, `exchange`, `routingKey`, `body` | `{}` | schedule `body` through the library's scheduler, opening one for this case on first use |
| `request` | `exchange`, `routingKey`, `body`, `timeoutMs` | `{"reply": value}` | a request/reply call with the library's default reply queue and JSON codec, opening one requester per destination for this case on first use. Failure kinds: `decode`, `timeout`, `responder` |

### Streams and telemetry

| op | arguments | result | what it does |
|---|---|---|---|
| `declareStream` | `queue`, `maxAgeMs` | `{}` | declare a stream through the library's stream helper with that retention |
| `readStream` | `queue`, `handle`, `offset` (`first` or `next`), `behaviour`? | `{}` | read the stream through the library's stream reader with its default recovery and its default handling of a failed handler; deliveries are counted under `handle` exactly like `consume`, and read back with `handled`. `behaviour` is `consume`'s: the handler fails (the library's ordinary handler failure: throw, raise, return an error) for the first `n` deliveries of an id in `failFirst` |
| `metrics` | — | `{"names": [...], "samples": [{"name", "tags"}]}` | every metric the library reported to its telemetry seam since `begin`, one sample per report, through a recorder the driver installs at `begin` |

### Replay

| op | arguments | result | what it does |
|---|---|---|---|
| `replay` | `from`, `queue`, `ids` | `{"replayed": n}` | one call of the library's replay with a filter, and nothing after it: take messages off `from` (a `{queue}.dlq` or `{queue}.parked` queue) and republish them to `queue` through the default exchange, with the library's default replay settings (attempts restarted, no limit, no deadline). The filter decodes the body as JSON and accepts a message exactly when `body.id` is one of `ids` (a list of strings); everything else is passed over. `replayed` is the number the library reports it moved. Answer as soon as the library's call returns — no sleep, no settle, no follow-up queue read — because the case checks the source queue the moment the answer arrives |

`from` and `queue` are both given, so each library uses whichever its API
takes: Java `mq.replay(queue)` (which drains `queue + ".dlq"`), .NET
`mq.Replay(from)` (which derives `queue` from the suffix), Go
`patterns.Replay(ctx, conn, ReplayFrom{Queue: from, Exchange: "", RoutingKey: queue, Filter: ...})`,
Python `replay(connection, from, exchange="", routing_key=queue, only=...)`,
Ruby `Patterns.replay(connection, from:, exchange: "", routing_key: queue) { ... }`.
A library whose replay raises reports it as a failure with kind `other`.

### Mandatory publishes

`mandatory: true` is the library's mandatory switch, `false` its opt-out:
Java `publisher.with(PublishOptions.defaults())` (mandatory by default) /
`PublishOptions.defaults().allowUnroutable()`, .NET `PublishOptions.Defaults()`
(mandatory by default) / `.AllowUnroutable()`, Python
`mq.publisher(exchange, routing_key, mandatory=True)`, Ruby
`mq.publish(payload, to:, exchange:, mandatory: true)`, Go
`acemq.NewPublisher[T](conn, exchange, routingKey, acemq.Mandatory[T]())`. A
returned publish is `unroutable` and a nacked one `nacked`: Python
`PublishError.unroutable`, Ruby `PublishError#unroutable?`, Go
`errors.As(err, &*PublishFailedError)` and its `Unroutable` field; Java and .NET
raise one `PublishFailedException` for both, so their drivers read the message
(`could not be routed`, `matched no queue`).

### Idempotent consumers

`idempotent: true` on `consume`: Java
`ConsumerOptions.prefetch(n).idempotent(InMemoryIdempotencyStore.forOneDay())`,
.NET `ConsumerOptions.Prefetch(n).Idempotent(InMemoryIdempotencyStore.ForOneDay())`,
Python `mq.consume(queue, idempotent(InMemoryIdempotencyStore(), handler))`,
Ruby `mq.consume(queue, &Patterns.idempotent(Patterns::InMemoryIdempotencyStore.new) { ... })`,
Go `patterns.Idempotent(patterns.NewInMemoryIdempotencyStore(ttl), handler)`.
No `key` argument: the case is about each library's default key.

### Pipelines

| op | arguments | result | what it does |
|---|---|---|---|
| `pipeline` | `name`, `steps` (step names, in order), `handle`, `behaviour`? | `{}` | declare and start a pipeline named `name` with those steps: a direct exchange `name`, a queue `{name}.{step}` bound with the step's name, a consumer on each, following the slip each message carries. Every step's handler is the identity on the JSON body: it counts `body.id` under `handle` (read back with `handled`) and returns the body unchanged, so the message goes wherever its slip says next. `behaviour` maps a step name to `consume`'s behaviour (`{failFirst: {id: n}, sleepMs}`): that step's handler counts the delivery, sleeps `sleepMs`, and fails with the library's ordinary retryable failure (throw, raise, return an error) for the first `n` deliveries of an id in `failFirst`; a step not named in it is the identity. No retry policy is configured on any step or on the pipeline: each step is exactly what the library builds when the caller configures none. The driver publishes nothing; the runner sends messages in, with a slip of either form already written |

Java `mq.pipeline(name, JsonNode.class).step(s, JsonNode.class, identity)...build()`
(`AceMq.pipeline`, `PipelineBuilder.step`, `PipelineBuilder.build`), .NET
`mq.Pipeline<T>(name).Step<T>(s, identity)...BuildAsync()` with a JSON-node
reference type for `T`, Go
`patterns.NewPipeline[T](ctx, conn, name, patterns.PipelineStep(s, identity)...)`,
Ruby `Patterns::Pipeline.new(name, steps)` and, on each `{name}.{step}`,
`pipeline.follow(mq) { |m| identity }`, Python (no pipeline builder) the
exchange, queues and bindings through its topology helpers and, on each
`{name}.{step}`, `mq.consume(queue, follow_slip(mq, identity, pipeline=name))`.
Whatever the library's pipeline does not declare itself, the driver declares
with the library's topology helpers, never with raw channel calls.

A failing step under `behaviour` fails inside the step's own handler, the
function the driver passes to the library, never in a wrapper around the
library's step: Java's `Step` throws, .NET's step delegate throws, Go's step
function returns an error, Ruby's `follow` block raises, Python's stage raises
inside `follow_slip`. The driver calls nothing that sets a retry policy: no
`PipelineBuilder.withRetry` (Java), `WithRetry` or `WithRetryDelay` (.NET),
`StepRetry` (Go), `retry_policy:` (Ruby) or `retry=` (Python), and no
connection-wide default either.

Arguments a driver does not recognise are ignored, so a case may add an
optional argument without breaking older drivers; a new **op** is a new TCK
release, on the 0.3.x line like every other change, and its cases start in
`cases/pending/` until every driver answers it. A case whose outcome depends on an argument (`mandatory`,
`idempotent`, `consume` without `retry`, `readStream` with `behaviour`, `pipeline` with `behaviour`) fails
on a driver that ignores it, which is one reason such a case starts in
`cases/pending/`.

## Timing

The runner measures every driver step itself (`elapsedMs`), from writing the
request to reading the answer. A driver does not report its own timings.
