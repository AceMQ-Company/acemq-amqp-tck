# 09 — The idempotent consumer

A consumer made idempotent claims a key for each message before its handler
runs and confirms the claim when the handler succeeds, so a redelivered or
republished copy of a message it already handled is not handled again.

### AMQP-IDEM-001 (MUST) A message id already handled is acknowledged without calling the handler

Cases: IDEM-001

A delivery whose key was confirmed by an earlier, successful handling is
acknowledged and its handler is not called: not dead-lettered, not parked, not
requeued. The key is `x-acemq-id`.

### AMQP-IDEM-002 (MUST) Without `x-acemq-id`, the key is the AMQP `message_id`

Cases: IDEM-001

A message from a publisher that is not an AceMQ library carries an AMQP
`message_id` and no envelope headers. The idempotent consumer keys it by
`message_id` (the property AMQP-ENV-002 makes equal to `x-acemq-id`), so two
copies of it are one message. A key generated afresh for each delivery
deduplicates nothing.
