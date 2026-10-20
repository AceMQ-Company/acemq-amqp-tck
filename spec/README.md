# The AceMQ AMQP behavioural specification

What every AceMQ AMQP library does, stated once, so that five implementations
are one product. Each requirement has an identifier, a level and, where the
behaviour is observable from outside the library, at least one case in
[`cases/`](../cases) that proves it.

## Reading a requirement

```
### AMQP-SCHED-001 (MUST) A due message nothing is bound for is kept
```

- **Identifier** — `AMQP-<AREA>-<NNN>`. Never reused, never renumbered. A
  requirement that is withdrawn stays in its file, struck through, with the
  version that withdrew it.
- **Level** — the words of RFC 2119 / RFC 8174: **MUST**, **MUST NOT**,
  **SHOULD**, **SHOULD NOT**, **MAY**. A MUST is a case that fails the build.
  A SHOULD is written down so a divergence is a decision rather than an
  accident; it may or may not have a case.
- **Cases** — the line under the heading names the cases that exercise it.
  `none yet` is an honest answer and appears in [ROADMAP.md](../ROADMAP.md).

## Areas

| File | Area | Prefix |
|---|---|---|
| [01-envelope.md](01-envelope.md) | the headers a publish puts on the wire | `AMQP-ENV` |
| [02-publishing.md](02-publishing.md) | confirms, mandatory, what is published on the user's behalf | `AMQP-PUB` |
| [03-retry.md](03-retry.md) | the retry ladder, hops, dead-lettering, naming | `AMQP-RETRY` |
| [04-scheduler.md](04-scheduler.md) | delayed delivery | `AMQP-SCHED` |
| [05-request-reply.md](05-request-reply.md) | request/reply | `AMQP-RR` |
| [06-streams.md](06-streams.md) | stream queues and readers | `AMQP-STREAM` |
| [07-telemetry.md](07-telemetry.md) | metric names, tags and outcomes | `AMQP-TEL` |
| [08-replay.md](08-replay.md) | taking dead-lettered messages back | `AMQP-REPLAY` |
| [09-idempotency.md](09-idempotency.md) | the idempotent consumer | `AMQP-IDEM` |
| [10-routing-slip.md](10-routing-slip.md) | the route a message carries | `AMQP-SLIP` |

## Terms

- **Library** — one of `acemq-java-amqp`, `acemq-python-amqp`,
  `acemq-ruby-amqp`, `acemq-dotnet-amqp`, `acemq-go-amqp`.
- **On the user's behalf** — a publish the library makes that the user's code
  did not call publish for: a retry hop, a dead-letter or park, a scheduler
  hop or due delivery, a reply, an outbox relay.
- **Broker-observable** — visible to a third party through the RabbitMQ
  management API without the library's cooperation. Cases assert on this
  wherever the behaviour allows it, because it is the one view no library can
  shade.
