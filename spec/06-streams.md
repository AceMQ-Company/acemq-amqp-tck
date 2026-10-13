# 06 — Streams

### AMQP-STREAM-001 (MUST) A reader resumes where it was after a reconnect

Cases: none yet

After the connection is lost and recovered, a stream reader continues from the
offset after the last message it delivered — not from the start, not from the
end, and not from where it first attached.

### AMQP-STREAM-002 (MUST) The default stream age is spelled `1h`

Cases: none yet

A stream declared with the default retention carries `x-max-age` as the string
`1h`, not `3600s`, so that two libraries declaring the same stream agree and
the broker never refuses the second declaration as inequivalent.

### AMQP-STREAM-003 (MUST NOT) Retry on a stream appends to the stream

Cases: none yet
