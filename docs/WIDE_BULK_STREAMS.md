# 16-byte streamed bulk copies

Keep the128-byte scalar expansion budget and existing small-copy/move snapshots.
Copies and overlapping moves above that budget, plus dynamic counts, now use
normal16-byte vector LOAD/STORE through existing IR type52 (U32x4). Forward loops
copy complete16-byte chunks then an exact byte tail. Backward moves process the
high byte tail first, then complete chunks downward. Every source chunk is read
before its destination write; no access exceeds the supplied extent. Normal
unaligned memory remains supported. Zeroing stays on the existing8-byte path.

This independently extends the prior scalar bulk lowering using the shared
vector/control graph and ordinary matching/allocation. No new target instruction
or changed ABI is introduced. Small-copy field promotion remains unchanged.
Fixed416-byte copy graphs retain32 cells; dynamic copy33, move67, zero29, matching
the scalar-loop source. Zero-dynamic object is byte-identical to the baseline.

Debug/ASAN: expanded jit-bulk guard pages and full byte comparisons pass across
16-byte boundaries, alignments0/1/3/7/8/15 and overlapping moves at±15/16/17/31
in addition to existing cases. bulk, jit-bulk-pressure, inline-stack-results,
static-stack, jit-mem2ssa and linked aot-bulk-link all pass. The AOT caller links
all nine generated bulk/pressure objects and checks byte oracles and ABI clobbers.

## O3 copy diagnostic

One identical C caller object invokes opaque kernels one million times. Complete
guards, copied bytes and unchanged source are independently checked before/after
timing. Eight rotating process-CPU-clock samples after excluded warmups.
LLVM O3 kernel is compiled from equivalent Coil aggregate assignment using a
byte-aligned416-byte payload; it lowers to memmove. An earlier u64-array reference
was replaced to avoid requiring alignment on unaligned cases; those measurements
are discarded. No bootstrap acceptance is inferred.

| Alignment | Scalar8 ms | Vector16 ms | LLVM O3 ms |
|---|---:|---:|---:|
|0|16.8095|9.2605|5.8370|
|1|16.8835|9.4085|5.8965|
|7|16.8455|9.3665|5.8660|
|15|16.7610|9.4500|5.8330|

Aligned copy improves44.9% (1.815×), but remains1.59× LLVM runtime on this kernel.
Full compiler integration, generation cost and bootstrap runtime remain pending.
Raw sources, caller, assembly, sample/object hashes and logs are in validation/
wide-bulk-streams. No global installation change.
