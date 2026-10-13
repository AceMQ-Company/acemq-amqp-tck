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
| `refused` | the broker nacked a publish, or back pressure refused it |
| `responder` | a request/reply responder reported a failure |
| `unsupported` | the op or an argument is not implemented by this driver |
| `other` | anything else |

## Operations

Every driver implements every operation below. An op the driver does not list
in `hello` fails every case that uses it.

| op | arguments | result | what it does |
|---|---|---|---|
| `hello` | — | `{"library", "version", "ops": [...]}` | the library's name and version as the library reports it; the ops implemented |
| `begin` | `case`, `clientName` | `{}` | close whatever the previous case left; open a fresh connection whose client name is `clientName` (it is what `x-acemq-origin` is built from) |
| `end` | — | `{}` | close everything this case opened: consumers, schedulers, requesters, the connection. Idempotent: called again after a case's own `end` step |
| `publish` | `exchange`, `routingKey`, `body`, `envelope`? | `{"messageId"}` | publish `body` (a JSON value) with the library's JSON codec and default publish settings. `envelope` may carry `id`, `type`, `version`, `correlationId`, `causationId`, `headers`; any field absent means "let the library decide" |
| `consume` | `queue`, `handle`, `prefetch`, `retry: {maxAttempts, delayMs}`, `behaviour: {failFirst: {id: n}, sleepMs}` | `{}` | declare `queue` the way the library's own topology declares a consumed queue with that retry policy (source queue, dead-letter and parked queues, rungs), then consume it with a fixed-delay retry policy. The handler reads `body.id`, counts the delivery, sleeps `sleepMs`, and fails (with the library's ordinary retryable failure) for the first `n` deliveries of an id named in `failFirst` |
| `handled` | `handle` | `{"counts": {id: n}, "redelivered": {id: n}}` | how many times the handler has been called for each id, and how many of those deliveries carried the AMQP `redelivered` flag (ids with none are left out) |
| `schedule` | `delayMs`, `exchange`, `routingKey`, `body` | `{}` | schedule `body` through the library's scheduler, opening one for this case on first use |
| `request` | `exchange`, `routingKey`, `body`, `timeoutMs` | `{"reply": value}` | a request/reply call with the library's default reply queue and JSON codec, opening one requester per destination for this case on first use. Failure kinds: `decode`, `timeout`, `responder` |

Arguments a driver does not recognise are ignored, so a case may add an
optional argument without breaking older drivers; a new **op** is a new TCK
minor version.

## Timing

The runner measures every driver step itself (`elapsedMs`), from writing the
request to reading the answer. A driver does not report its own timings.
