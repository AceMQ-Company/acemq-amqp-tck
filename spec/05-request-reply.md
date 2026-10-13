# 05 — Request/reply

A requester publishes with `reply_to` set to its reply queue and pairs the
answer by `x-acemq-correlation` (and the AMQP `correlation_id` property, which
it also sets).

### AMQP-RR-001 (MUST) A reply is paired by correlation and decoded with the requester's codec

Cases: RR-001

### AMQP-RR-002 (MUST) An undecodable reply is raised promptly as a decode error

Cases: RR-002

A reply the requester's codec cannot read is accepted off the reply queue and
raised to the caller as the codec's decode error as soon as it arrives —
not parked, not dead-lettered, and not left for the caller to wait out the
request timeout.

### AMQP-RR-003 (MUST NOT) A reply queue's consumer declares dead-letter or parked queues

Cases: RR-001, RR-002

The reply queue is a mailbox for one process; no `{reply queue}.dlq` or
`{reply queue}.parked` is declared for it, before, during or after a call.

### AMQP-RR-004 (MUST) No reply in time is a timeout error

Cases: RR-003

Raised when the timeout elapses, not before, and the request itself is left
where it was published.

### AMQP-RR-005 (MUST) A responder failure is raised as a responder error

Cases: RR-004 (pending)

A reply carrying the `acemq-error` header (the shared, unreserved namespace,
so that a responder in any language can set it) is raised as the responder's
failure, checked before the body is decoded.
