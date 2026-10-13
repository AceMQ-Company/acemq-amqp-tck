# 04 — Scheduler

The scheduler holds a message in broker-side rungs (`acemq.schedule.*`) and
publishes it to its destination when it is due.

### AMQP-SCHED-001 (MUST) A due message nothing is bound for is kept

Cases: SCHED-001

When the due delivery is unroutable (returned) or refused, the message is not
dropped, dead-lettered or acknowledged away. It goes back through the
ten-second rung and is tried again, until it is delivered.

### AMQP-SCHED-002 (MUST NOT) Dead-letter a due message to a queue nothing reads

Cases: SCHED-001

In particular, nothing is ever moved to `acemq.schedule.due.dlq` (or any other
`.dlq` / `.parked` queue) because its destination was not yet bound.

### AMQP-SCHED-003 (MUST) A kept message is delivered once its destination exists

Cases: SCHED-001

Within one ten-second rung of the binding appearing, and exactly once.

### AMQP-SCHED-004 (MUST) Never early

Cases: none yet

A scheduled message is not delivered before its due time.
