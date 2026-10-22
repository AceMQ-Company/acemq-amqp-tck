# 11 — The claim check

A payload too large for a broker goes to a store, and the message carries a
key to it. A message checked in by one library is redeemed by another, so the
framing of the body and the layout of the filesystem store are wire format.

### AMQP-CLAIM-001 (MUST) The framing

Cases: CLAIM-001

A body written by the claim-check codec starts with three bytes: `0xAC`
(magic), `0x01` (version), then `0x00` when the payload follows inline, exactly
as the codec it wraps wrote it, or `0x01` when what follows is the store's key
as bare UTF-8 — no URI, no scheme. A payload whose encoded size is at or above
the codec's threshold is checked in; one below it is framed inline. The
message keeps the wrapped codec's content type. The framing is the contract,
not a header: a header can be dropped on the way and the body cannot, so
`x-acemq-claim` (AMQP-ENV-001) is not what a consumer decides on.

### AMQP-CLAIM-002 (MUST) The filesystem store

Cases: CLAIM-001, CLAIM-002

The filesystem store keeps a payload in one file, named by its key, directly
in the store's directory, holding the encoded payload and nothing else. Keys
are safe file names. A consumer whose codec is the claim-check codec over the
filesystem store at the same directory redeems a key that another library
checked in, and hands its handler the payload as if it had travelled inline.
Reading a claim check never deletes it: retention belongs to whoever owns the
store, and a second consumer or a replay must still find it.
