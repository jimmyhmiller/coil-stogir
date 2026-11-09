# Allocation regions and loop-entry eviction

Runtime-first research toward ≥5× LLVM O3 generation speed and ≤1.10× LLVM
runtime. Both remain acceptance criteria; generation regressions are permitted
while discovering the needed runtime optimizations.

## Reproducible allocator trace

`allocation-snapshot.coil` emits deterministic input and linear-scan output
records when `private/with-allocation-trace` is enabled. The Coil adapter enables
it for the function selected by `COIL_STOGIR_GRAPH` when `COIL_TPDE_STATS=1`.
Snapshots include register classes, live ranges, use constraints, hints, frame
slots and owner maps, spill shapes, split metadata, instruction positions and
CFG edges. Tracing does not change allocator decisions.

`primitive.trace` was captured with the prior allocator and the BASE + PREDICT
settings below. Before allocator edits, the generated replay reproduced all
381 output parts exactly. New policies deliberately change that output; the
original output records are retained as the comparison oracle.

```
python3 docs/benchmarks/allocation-regions/replay.py \
  docs/benchmarks/allocation-regions/primitive.trace \
  build/allocation-regions/replay.coil --regions
COIL_LIBRARY_STATE=0 "$STOGIR_TEST_COIL" run \
  build/allocation-regions/replay.coil --backend stogir -O3 --no-debug --debug-checks
```

The generator emits `.expected` with the captured linear-scan result. Without
`--regions`, replay output is directly comparable with that file when running
the captured allocator version. `--regions` additionally reconstructs eligible
control-only regions from the recorded schedule and CFG and verifies the edited
assignments. It has no hard-coded function references or positions.

## Findings and changes

In `primitive-providers-in`, the inner loop's empty exit block at [1128,1132)
inherits spill assignments from the cold body. Five outer values are still in
registers at source position 351, but acquire stack locations in the bypass and
reload on the outer backedge. This creates avoidable memory traffic even when
the inner body never executes.

`allocation-regions.coil` runs after linear scan and before allocation
verification/location indexing. For a block containing only its start and END,
with exactly one predecessor, it inherits predecessor locations simultaneously.
It rejects partial liveness, register-required uses, fixed interference and
missing source values. Every affected interval is split around the region;
outside pieces retain their assignments. The ordinary edge resolver still
handles all actual location changes. No CFG edges or program checks are removed.

The real-function replay changes those five locations; applying the pass to all
eligible blocks changes 21 locations. Emitted code confirms five reloads vanish
from the zero-trip path. Focused tests cover simultaneous register exchanges,
preservation outside the region and the rejection conditions.

A second finding: proactive loop eviction used the current scan position while
ordinary blocked eviction already used `active-eviction-cut`. Using that same
legal split rule in proactive eviction moves spills of values 87 and 209 from
315/338 to 177, before the outer loop. It keeps past uses and required uses in
the correct assigned prefix. The strengthened loop-entry regression fails on
the preceding library and passes on the new one.

## Measurement setup

Matched hosts emit the fixed Coil source `stogir-branch-fusion` at d1efe960.
BASE + PREDICT:

```
COIL_STOGIR_INLINE=small=80,small-scope=any,hoist=1
COIL_STOGIR_LOOP_EVICT=1
COIL_STOGIR_LOOP_RELOAD=1
COIL_STOGIR_PREDICT=1
```

The previous host is `stogir-inline-policy/build/hp17/predict2/bin/coil`.
LLVM is `stogir-branch-fusion/build/n8-full8/host-llvm/bin/coil`.
New hosts, original trace, replay output and raw diagnostics are under each
worktree's `build/allocation-regions/`. The alternating-order, hash-checking
driver is `../deferred-loop-splits/compare.py`.

First three-round measurement (empty-block pass alone):

| Host | Minimum B cycles | Median B cycles |
|---|---:|---:|
| LLVM | 44.928 | 47.555 |
| Prior | 56.745 | 57.653 |
| Regions | 56.021 | 56.820 |

Minimum/median changes: −1.28%/−1.44%. Retired instructions fall by about 1.7B
from ~211.7B. Every run emitted the identical seed object
`9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.
Load varied; the follow-up round includes both policies separately.
One-off generation: regions 9.083s; regions + earlier eviction 8.944s. These
are not paired isolated generation measurements.

## Validation status

Region unit tests, loop-entry splits, indexed pressure oracle, AArch64 allocation,
native GP/SIMD and switch pressure, private call allocation, module execution,
and block layout pass at the checkpoints described above. Exact allocation
replay passes verification before and after region changes. Full suite and FAST
remain pending. Nothing installed or pushed; goals remain unmet.

## Follow-up and retained implementation

Second matched round:

| Host | Minimum B cycles | Median B cycles |
|---|---:|---:|
| LLVM | 44.563 | 45.720 |
| Prior | 56.150 | 57.430 |
| Regions | 55.377 | 56.674 |
| Regions + earlier eviction | 54.939 | 59.780 |

Region-only minimum/median improve 1.38%/1.32%, consistent with the first round.
Its minimum ratio is still 1.243× LLVM. All twelve outputs match the seed hash.
Earlier eviction has a faster best run but much worse median and large spread;
its incremental benefit is not established. It is saved in
`early-eviction.patch`, including its regression test, and removed from live
sources. Do not treat the description above as a shipped early-eviction fix.

The retained region pass verifies allocations before and after modification.
The full standalone suite is being run on frozen source; this section will be
updated with the authoritative results. Quick FAST and remaining delivery gates
are also required before promotion. No target is marked achieved.

## Completed validation

Final frozen source: 297 standalone programs, 295 pass. The two failures are
`jit-parameter-specialize` ("expected expansion") and `private-leaf` ("wrong
signature accepted"). Both were rerun against the preceding library and fail
with the same assertions; they are pre-existing and remain open.

All **73 linked AOT consumers pass** with fresh fixtures. The generic sweep
omits their link flags and is not valid evidence for these consumers. The
separate `linked.py` run used the prior validated fixture manifest, supplemented
by explicit README/documentation commands and the mem2ssa producer's object
path. All 5,410 unique fixtures were newer than the library checkpoint and were
copied to a private directory before linking, with SHA-256 recorded in the
build artifacts. `link-manifest.json` records the selected fixture paths.

Quick FAST passes (63s under concurrent validation load). Full FAST/live emission
and current-source bootstraps remain final acceptance gates. The two performance
targets have not been achieved. Nothing installed or pushed.

## Generation cost on the final candidate

Three alternating default-policy emits of the fixed compiler workload:

| Candidate | Minimum generation seconds | Median generation seconds |
|---|---:|---:|
| Prior | 6.984 | 7.070 |
| Regions, including before/after verification | 7.269 | 7.377 |

Generation costs +4.08% minimum / +4.34% median. Output objects differ as expected
because allocation changes; this is not an output-preserving generation change.
A fresh LLVM generation comparison is still required to establish the absolute
5× ratio. This cost is accepted for runtime-first research, not declared compliant
with the final generation target.

Next runtime work: prove redundant bounds comparisons from dominating branches
and integer range facts. The allocation trace and assembly expose the same
index/length comparison repeated on paths where the first branch already proved
it. Retain all checks without a proof; use matched-host timing and output identity
for every candidate. The goal remains active.

Final candidate identity check: after retaining both verifier calls and excluding
external entry blocks, it emits a byte-identical host object to the measured
region-only host (`8449a7d2460a32f66f5bcc2a22ddcf8245a1c7f5eb9fd828d24fd9f33caca4b7`).
Thus the retained implementation produces the machine code used in the reported
runtime measurements. See `final-identity.txt`.
