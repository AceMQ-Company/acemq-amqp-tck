# 08 — Replay

A replay takes messages off a dead-letter or parked queue (`{queue}.dlq`,
`{queue}.parked`) and republishes them to the queue they failed on. A filter
picks which ones go; the rest stay where they are. The headers a replayed
message carries are AMQP-ENV-013.

### AMQP-REPLAY-001 (MUST) A filtered replay returns only once every message it passed over is back

Cases: REPLAY-001

When a replay with a filter returns, every message the filter rejected is
ready again on the queue it was taken from, in the same number: a queue-depth
read made by anyone — the library's own pending count, or the broker —
immediately after the call returns sees all of them. Holding them
unacknowledged while the replay runs is fine; handing them back with a
fire-and-forget reject or nack and returning without waiting for the broker to
have them is not, because the caller's next question is "how many are left".

### AMQP-REPLAY-002 (MUST) A matched message is replayed exactly once

Cases: REPLAY-001

Every message the filter accepts is on the target queue exactly once and gone
from the queue it was taken from when the replay returns, and the replay
reports how many it moved.

### AMQP-REPLAY-003 (MUST) A replay restarts the attempt and clears the error, and nothing else

Cases: REPLAY-002 (pending)

With the default settings (attempts restarted), the replayed message carries
`x-acemq-attempt` 1 and no `x-acemq-error`; `acemq-replay-count` is one more
than the integer it arrived with (1 when it had none). Every other header,
the body, `content_type` and `message_id` are unchanged.
