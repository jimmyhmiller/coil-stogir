# Allocation regions: independent-block probe

The goal remains ≥5× LLVM generation and runtime ≤1.10× LLVM on the fixed
compiler workload. Runtime-first research may increase generation cost. This
probe does **not** improve the best runtime policy.

## Evidence and rejected approach

The fresh induction baseline snapshot reproduces its captured allocator output
exactly. The existing empty-block inheritance then changes 25 locations, giving
402 output parts. Generalizing register inheritance to instruction-containing
blocks finds only one conflict-free candidate in this graph: parent 89 in the
block at positions [980,986). Occupied registers prevent almost all other
changes; retaining predecessor assignments alone is insufficient.

`regional-allocation.coil.in` is an isolated experimental allocator, **not
integrated or vendored into the compiler**. It clips original intervals and
constraints into CFG blocks, preserving lifetime holes and fixed reservations.
It remaps hint indices, uses incoming physical registers as preferences, runs
the existing allocator independently for each block, and verifies every local
and combined result. The ordinary edge resolver would reconcile assignments.
It checks that the partition preserves total interval coverage. This is an
allocation replay experiment; native execution of this alternative allocator
has not been validated or benchmarked.

The unrestricted version increases transfers substantially:

| Logical allocation metric | Baseline | Independent blocks |
|---|---:|---:|
| Output parts | 402 | 1,995 |
| Edge transfers, including PHIs | 85 | 469 |
| Edge memory transfers | 48 | 89 |
| Internal transfers | 17 | 62 |
| Internal memory transfers | 9 | 55 |

These are static logical transfers, not executed instruction counts or cycle
measurements. Parallel-copy cycles, spill-home store elimination, prologue cost,
and instruction-selection effects are not modeled. Nevertheless, the large
increase provides no reason to integrate the unrestricted approach.

The selective probe starts from the existing global allocation and reallocates
each of the 111 blocks separately, using its neighbors' physical locations as
preferences. All candidates pass the allocation verifier. A proxy cost assigns
one unit to register/constant copies, three to stack copies, and weights block
costs by 10^loop-depth; edge costs use the shallower endpoint's depth. Only block
109, [1110,1116), improves this proxy (280 to 0). It is an outer-loop exit, not
the hot nested-loop bypass. This does not demonstrate a material runtime gain.

## Reproduction

The tool creates an isolated copy of library `3932dc0` under the requested
output directory, adds the experimental module there, and runs with the fixed
test compiler. It does not edit the live library or integration.

```
python3 docs/benchmarks/regional-allocation/reproduce.py "$STOGIR_TEST_COIL" \
  build/regional-reproduction \
  --trace docs/benchmarks/regional-allocation/primitive.trace.gz
python3 docs/benchmarks/regional-allocation/analyze.py build/regional-reproduction
```

The baseline, independent allocation and all selective candidates were rerun
through this exact workflow successfully. Compressed logs, `result.json` and
`analysis.json` retain the evidence. The replay tool also accepts the older
version-1 trace, whose transfer analysis lacks alias/PHI information.

## Retained diagnostic improvement

Library `dd930d7` extends allocation snapshots to version 2, recording canonical
coalescing aliases and each edge-indexed PHI copy. The selected function supplies
48 aliases and 68 PHI copies. This lets analysis include the boundary transfers
omitted by the old ordinary-values-only count. The replay generator accepts both
versions. Missing physical locations are errors in the analyzer, not zero-cost
assumptions.

The final candidate, rebuilt after vendoring and its provenance update, emits
exactly the measured induction host object while tracing:
`221639412cd1c1c5dd75b714943a35c3043deeed7c27fbdae1fbc55582b9f09b`.
Generator identity is in `identity.json`. Source and vendor library trees match.
The existing allocation-region regression passes, and exact allocation replay
matches before and after adding the metadata. No allocation decision changes.
A full library/FAST repeat was not performed for this diagnostic-only change;
the preceding full validation remains documented in the load-hoisting report.

Next measure broader inlining with the retained region and induction passes.
The prior broad-inlining regression predates those changes. This is an
interaction experiment, not an assumption that the spill problem is solved.
No install or push has occurred.
