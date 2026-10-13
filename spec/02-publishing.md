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

### AMQP-PUB-004 (MUST) Back pressure is distinguishable from a publish that may be lost

Cases: TEL-002, TEL-003

A publish the library declines to send because the broker is blocking
publishers (a resource alarm) raises an error that says nothing was sent,
distinct from a broker `basic.nack`, which says the broker would not keep a
message it was given. See also AMQP-TEL-003.

### AMQP-PUB-005 (MUST) A publish into a blocked broker is bounded

Cases: TEL-003

A publish that is waiting on a broker which has blocked publishers (a resource
alarm) fails within the library's blocked timeout rather than waiting for the
alarm to clear. It is reported as possibly published (`failed`) when it was
written before the block was known, and as `paused` / `refused` when the
library knew and did not write it.
