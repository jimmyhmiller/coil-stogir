# Bounded constant bulk expansion probes

Standalone 0d6d545 probes a generic 128-byte constant bulk expansion budget,
compared with production's 64 bytes. Separate branch67e2e46 probes512 bytes;
1af5e3e fixes the expanded pressure fixture's own storage sizes. Neither policy
is adopted. These are local lowering budgets, not copied upstream thresholds.
All paths use the existing scalar/control IR and optimizer; no96-byte special
case or copy alias shortcut is introduced.

The64-byte budget lowers96-byte value copies to loops. Existing scalar memory
promotion handles fixed private stack offsets but conservatively rejects the
variable offsets in those loops.128 exposes the96-byte operations before
promotion; the read-only projection reduces from two copy loops to two loads,
arithmetic and return. Graph itself is416 bytes, motivating the separate512
probe rather than assuming128 covers every aggregate.

Validation: bulk input/no-op/bounded-graph checks, guarded-page copy/move/zero
matrix with71/72/95/96/97 and127/128/129 boundaries, pinned values live across
calls and spills/dynamic frames, and the existing memory-promotion oracle pass
under debug checks and AddressSanitizer.512 adds511/512/513 boundaries and larger
pressure cases; all pass after increasing fixture allocation/buffers to cover
the new extents plus offsets. The initial pressure run was invalid because its
old200-byte buffers and512-byte allocation were too small; no backend failure
inferred from that run. Snapshot, overlap, tail and barrier checks remain.

Fixed aggregate sweep, identical source and opaque C caller,8 rotating generation
and32 CPU samples after warmup.200000 calls per size, independent checksum and
source-preservation checks on64 varying records:

| Budget/backend | Generation ms | Object B |
|---|---:|---:|
|64 Stogir |1.154|2385|
|128 Stogir|1.139|1873|
|512 Stogir|1.383|1489|
|LLVM O3|17.311|1016|

| Size B |64-budget CPU ms|128-budget CPU ms|512-budget CPU ms|LLVM CPU ms|
|---|---:|---:|---:|---:|
|64|0.1800|0.1800|0.1785|0.1800|
|72|1.6950|0.1800|0.1770|0.1790|
|80|1.8245|0.1800|0.1765|0.1795|
|96|2.0585|0.1790|0.1770|0.1805|
|128|2.5860|0.1790|0.1770|0.1805|
|136|2.7040|2.6925|0.1795|0.1800|
|256|4.4965|4.5195|0.1780|0.2380|
|512|9.1640|8.3800|0.1795|0.1795|

512 gives broad local runtime improvement but19.84% higher generation cost on
this fixture.128 fixes the common96-byte case with unchanged generation time.
The128 policy is selected for the first new full-bootstrap diagnostic, which is
still pending. Do not substitute local results for the5x/within10% full compiler
goal. Raw scripts/source/results are in validation/bulk-expansion; full Coil
checkpoint artifacts will live outside the frozen compiler source SDK.
