# 10 — The routing slip

A message carries where it goes next; each step reads the slip, does its work,
moves the slip on and publishes to the next destination. There is no
coordinator, so the slip is wire format: a step written in one language must
continue a route written in another. It has two forms.

### AMQP-SLIP-001 (MUST) The route form

Cases: SLIP-001 (pending)

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

Cases: SLIP-002 (pending)

`acemq-routing-slip` is a JSON string
`{"steps": [{"exchange", "routingKey", "name"?}, ...], "done": [...]}`.
`steps[0]` is the hop being handled. A step that succeeds moves it to the end
of `done`, adding `completedAt` (ISO-8601 UTC), and publishes its output to
the new `steps[0]`'s exchange and routing key, which can be any destination,
not only a pipeline step. When both forms are present the itinerary is the one
followed.

### AMQP-SLIP-003 (MUST) A hop keeps the correlation and the form

Cases: SLIP-001 (pending), SLIP-002 (pending)

The message a step publishes carries the correlation of the one it handled,
`x-acemq-causation` set (to the handled message's id), and the slip in the
form it arrived in: a route arrives as a route and leaves as one.
