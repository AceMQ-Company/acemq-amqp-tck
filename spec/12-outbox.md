# 12 — The outbox

A message recorded in the caller's own transaction and published afterwards
by a relay. What reaches the broker has to be the message the caller recorded,
and nothing recorded may be lost between the store and the broker.

### AMQP-OUTBOX-001 (MUST) A relayed message is the message that was recorded

Cases: OUTBOX-001

The relay publishes the payload as the codec encoded it when the record was
made — the bytes, not those bytes encoded a second time — with the record's
content type and the envelope it was recorded with: the record's id as
`x-acemq-id` and `message_id`, the caller's correlation and headers, and every
default of AMQP-ENV-001..012 exactly as a direct publish of the same payload
would have them. The message is persistent. A record is published once: the
relay does not publish a record it has published already.

### AMQP-OUTBOX-002 (MUST) A record the broker did not take stays in the outbox

Cases: OUTBOX-002

A relay publish is an on-behalf publish (AMQP-PUB-001): mandatory and
confirmed. A record whose publish is returned unroutable, nacked or refused is
not marked published; the relay tries it again on a later pass, so once the
destination exists the message arrives. A relay that published without
`mandatory`, or marked a record before the confirm, loses it without a trace.
