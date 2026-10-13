# 02 — Publishing

### AMQP-PUB-001 (MUST) What is published on the user's behalf is mandatory and confirmed

Cases: none yet (the flags are not broker-observable; see ROADMAP)

Every publish the library makes on the user's behalf — retry hops, dead-letter
and park, scheduler hops and due deliveries, replies, outbox relays — is
published with `mandatory` set and waits for the broker's confirm, **whether or
not the user turned publisher confirms on for their own publishes**. The source
delivery is settled only after that confirm.

### AMQP-PUB-002 (MUST) An on-behalf publish that is not taken never loses the message

Cases: SCHED-001, RETRY-001

When an on-behalf publish is returned unroutable, nacked, refused or fails to
reach the broker, the message it was carrying is kept: the delivery it came
from is requeued or held, never acknowledged and never rejected without
requeue to a place nothing reads.

### AMQP-PUB-003 (MUST) An unroutable user publish is an error

Cases: none yet

A mandatory publish the broker returns raises (or returns) an error that says
it was unroutable, distinguishable from a refusal.

### AMQP-PUB-004 (MUST) A refused publish is distinguishable from a failed one

Cases: none yet

A broker `basic.nack` or a back-pressure refusal is reported as refused, not
as a generic failure. See also AMQP-TEL-003.
