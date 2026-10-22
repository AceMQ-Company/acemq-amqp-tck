# 10 — The routing slip

A message carries where it goes next; each step reads the slip, does its work,
moves the slip on and publishes to the next destination. There is no
coordinator, so the slip is wire format: a step written in one language must
continue a route written in another. It has two forms.

### AMQP-SLIP-001 (MUST) The route form

Cases: SLIP-001

A pipeline `{pipeline}` is a direct exchange of that name and a queue
`{pipeline}.{step}` per step, bound with the step's name. The route travels in
three headers:

| Header | AMQP type | Meaning |
|---|---|---|
| `x-acemq-route` | long string | the step names, comma-joined, in order |
| `x-acemq-route-position` | integer | how many steps are done: 0 at the first step |
| `x-acemq-route-id` | long string | the run, set once and carried unchanged |

A step that succeeds publishes its output to exchange `{pipeline}` with the
next step's name as routing key and the position one greater; the last step
publishes nothing.

### AMQP-SLIP-002 (MUST) The itinerary form

Cases: SLIP-002

`acemq-routing-slip` is a JSON string
`{"steps": [{"exchange", "routingKey", "name"?}, ...], "done": [...]}`.
`steps[0]` is the hop being handled. A step that succeeds moves it to the end
of `done`, adding `completedAt` (ISO-8601 UTC), and publishes its output to
the new `steps[0]`'s exchange and routing key, which can be any destination,
not only a pipeline step. When both forms are present the itinerary is the one
followed.

### AMQP-SLIP-003 (MUST) A hop keeps the correlation and the form

Cases: SLIP-001, SLIP-002

The message a step publishes carries the correlation of the one it handled,
`x-acemq-causation` set (to the handled message's id), and the slip in the
form it arrived in: a route arrives as a route and leaves as one.

### AMQP-SLIP-004 (MUST) A failing step with no retry policy makes one attempt

Cases: SLIP-003

AMQP-RETRY-008 for a pipeline step. A step whose own handler fails, in a
pipeline where no retry policy is configured for that step or the pipeline,
is attempted once: the message is dead-lettered to `{pipeline}.{step}.dlq` as
in AMQP-RETRY-005, with `x-acemq-attempt` 1, every header it arrived with
kept (the route headers and AMQP-ENV-014 included), and the handler is not
called for it again. Nothing is published to the next step. A retry delay the
pipeline applies by default is not a retry policy: retrying for ever, in the
consumer or by republishing to the step's queue, is not a default.

### AMQP-SLIP-005 (MUST) A hop carries the headers it does not own

Cases: SLIP-004, SLIP-005 (pending)

The message a step publishes onwards carries every header of the message it
handled that the slip does not change: application headers (a tenant, a trace
context, anything outside the `x-acemq-` namespace) and `x-acemq-` headers the
library does not know (AMQP-ENV-014), unchanged, in both forms. A hop is the
message moving on, not a new message written from the library's envelope
fields: a step written in one language must not strip what a step in another
language, or the service that started the run, put on it.
