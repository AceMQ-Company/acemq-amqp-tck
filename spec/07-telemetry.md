# 07 — Telemetry

The reference is `org.acemq.amqp.api.MetricNames` in `acemq-java-amqp`.

### AMQP-TEL-001 (MUST) Metric names

Cases: none yet

| Name | Kind |
|---|---|
| `acemq.publish.duration` | timer |
| `acemq.publish.total` | counter |
| `acemq.consume.duration` | timer |
| `acemq.consume.total` | counter |
| `acemq.consume.attempts` | distribution |
| `acemq.consume.in.flight` | gauge |
| `acemq.messages.retried.total` | counter |
| `acemq.messages.dead.lettered.total` | counter |
| `acemq.messages.set.aside.failed` | counter |
| `acemq.retry.rung.missing` | counter |
| `acemq.request.duration` | timer |
| `acemq.request.total` | counter |
| `acemq.outbox.lag` | gauge |
| `acemq.outbox.total` | counter |
| `acemq.pipeline.run.duration` | timer |
| `acemq.pipeline.run.total` | counter |

A language whose metrics convention forbids dots (Prometheus) renders them
with underscores; the dotted name is the one a library reports to its
telemetry seam.

### AMQP-TEL-002 (MUST) Tag names

Cases: none yet

`exchange`, `routing.key`, `queue`, `transport`, `message.type`, `target`,
`rung`, `outcome`, `pipeline`, `step`.

### AMQP-TEL-003 (MUST) Publish outcomes: `confirmed`, `unroutable`, `refused`, `failed`

Cases: none yet

`refused` is a broker nack or back-pressure refusal; `failed` is everything
else that kept a publish from being confirmed (connection lost, timeout). The
two are never merged.

### AMQP-TEL-004 (MUST) Consume outcomes

Cases: none yet

`acked`, `retried`, `dead_lettered`, `parked`, `rejected`, `in_progress`.
Request outcomes: `answered`, `timed_out`.
