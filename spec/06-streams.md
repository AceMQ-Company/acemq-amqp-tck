# 06 — Streams

### AMQP-STREAM-001 (MUST) A reader resumes where it was after a reconnect

Cases: STREAM-001

After the connection is lost and recovered, a stream reader continues from the
offset after the last message it delivered — not from the start, not from the
end, and not from where it first attached.

### AMQP-STREAM-002 (MUST) An hour of retention is spelled `1h`

Cases: STREAM-002

A stream declared to keep an hour carries `x-max-age` as the string `1h`, not
`3600s` (the largest whole unit of `D`, `h`, `m`, `s`), so that two libraries
declaring the same stream agree and the broker never refuses the second
declaration as inequivalent.

### AMQP-STREAM-003 (MUST NOT) Retry on a stream appends to the stream

Cases: STREAM-003 (pending)

A handler failure on a stream reader never publishes a copy of the message
back into the stream, which every other reader of that stream would then read.

### AMQP-STREAM-004 (MUST) A failing handler stops a stream reader at that message

Cases: STREAM-003 (pending)

By default, a handler failure on a stream reader stops the reader: the
subscription is closed, nothing after the failed message is handled, and no
copy of it is written anywhere (`{stream}.dlq`, `{stream}.parked`, the stream
itself). The stream is the record, so a reader restarted at the same offset
after a fix sees the message again. Skipping failures, or setting them aside,
is an option the caller turns on.
