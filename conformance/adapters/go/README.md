# Go adapter — `teambition/rrule-go`

```sh
go build -o rrulego_adapter .
python3 ../../score.py -- ./rrulego_adapter
```

Needs a Go toolchain and network access for the one module dependency; nothing
from this repository. The contract is [`../../PROTOCOL.md`](../../PROTOCOL.md).

Every case in the corpus is floating local time, so the adapter parses and
formats in `time.UTC` — a fixed-offset clock — and no timezone database enters
the answer. `rrule-go` is driven through `Iterator()` rather than `All()`,
because most rules here are infinite.

The result this produced is [finding 027](../../../findings/027-a-port-that-did-not-drift.md):
`rrule-go` v1.8.2 returns exactly what `python-dateutil` 2.9.0.post0 returns on
all 3813 corroborated cases. It is a port of dateutil by its own account, so it
is **not** an independent lineage and its score is not independent evidence.
