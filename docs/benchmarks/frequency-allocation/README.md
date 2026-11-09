# Coordinated allocation recoloring

This experiment finds a verified way to retain outer values across the inner-loop bypass in the captured `primitive-providers-in` graph. It is an offline prototype, not integrated into native code generation. There is no new cycle measurement or claim that the 5× generation / 1.10× runtime target is met.

## Evidence and algorithm

The version-2 snapshot from `../regional-allocation/primitive.trace.gz` replays exactly on library `bca7c4d`. The baseline is the retained induction policy, after the existing control-only inheritance pass. Its logical transfer counts match the previous analysis exactly: 85 edge copies, 48 involving memory; 17 internal copies, 9 involving memory.

`model.py` preserves live-range coverage per parent and position, lifetime holes, register classes, fixed-use and call-clobber reservations, canonical coalescing aliases and PHI input slots. It clips at existing CFG block boundaries without approximating ranges by bounding spans. Each virtual value has one canonical spill-home identity. Fixed physical reservations cannot move or spill. All constraints are independently checked before a candidate is accepted.

`recolor.py` groups existing interval children across a chosen region. Root moves try physical locations already present at connected copy endpoints. When that location is occupied, a bounded ejection chain can relocate interfering owners to other legal registers or a spill home. Fixed reservations remove impossible colors before search. A transaction is committed only if all allocation constraints hold and its complete transfer cost strictly decreases. The tested limits are depth 3, 100 search visits per root move, at most 8 reassigned pieces per transaction, and 32 improvement rounds. No workload names, measured execution counts or hardcoded physical assignments drive the algorithm.

The proxy charges one unit for register/constant copies and three for memory copies. Internal costs use 10^block-depth; edge costs use the shallower endpoint's depth. Physical duplicate copies at a transfer site are counted once. This deliberately includes entry/exit and PHI costs, unlike an isolated local instruction count. It still omits parallel-copy cycle expansion, canonical spill-home store elimination, rematerialization instruction counts, new spill-frame/prologue costs and actual branch frequency. It is not a hardware cycle estimate.

## Reproduced results

| Assignment | Edge copies | Edge memory copies | Internal copies | Internal memory copies | Weighted proxy |
|---|---:|---:|---:|---:|---:|
| Baseline | 85 | 48 | 17 | 9 | 503,298 |
| Whole-function bounded recoloring | 58 | 29 | 16 | 8 | 454,018 |
| Inner-region bounded recoloring | 84 | 47 | 15 | 7 | 386,298 |

The whole-function search stops after 13 improving transactions when no further improvement is found within its search limits. The inner-region search stops after 3. This is a bounded local search result, not global optimality. The Python prototype takes roughly 14 seconds for the whole function and 0.2 seconds for the inner region on this Mac; those are research-tool times, not compiler generation overhead.

The whole-function result also passes a second, direct replay on the original 402 allocation children: 14 register fields change, with no new split, spill home, frame change, live-range edit or constraint edit. Its output exactly matches the modeled assignment. This confirms that the bypass improvement can be implemented by recoloring existing pieces; the model's 1,950 block fragments need not become native allocation pieces. The emitted replay and exact plan are in `results/whole-children*`.

The enclosing-loop case directly addresses the bypass identified in the handoff:

| CFG edge | Baseline memory copies | Recolored memory copies |
|---|---:|---:|
| 203 → 19, first bypass entrance | 5 | 0 |
| 206 → 19, second bypass entrance | 5 | 0 |
| 61 → 55, shared continuation | 6 | 1 |
| 60 → 61, body return | 0 | 4 |

The remaining continuation copy carries parent 65. The other outer values retain their registers on the bypass; restores move onto the body path. Some memory stores counted here may already be eliminated by canonical spill-home logic, so only native disassembly and execution can establish the emitted and dynamic benefit. Full edge changes are retained in `results/enclosing-loop-edge-changes.json`.

This differs from the earlier independent-block probe: it can coordinate assignments across several blocks and charges all resulting boundaries. The prior independent allocator increased both edge and internal traffic and was rejected.

## Independent diagnostic solver

`oracle.py` formulates finite location domains with integer variables; `choices.py` uses explicit Boolean register choices and weighted MaxSAT. The solver is a diagnostic dependency only. It is never invoked by the prototype or compiler.

- The known outer-exit improvement is recovered: proxy 503,298 → 503,018, matching the previous single-block analysis.
- Altering only the inner-loop exit region has no improving assignment under this model's cuts and objective (integer solver reports unsatisfiable for a strict improvement).
- Whole interval pieces in the 30-block inner region have a proven proxy minimum of 386,298: the explicit-choice solver finishes with equal lower and upper bounds. The solver-free prototype reaches the same value.
- The larger enclosing-region solver times out with only a weak feasible improvement. It is not an optimality result. The bounded prototype finds a better practical assignment.
- Other integer searches time out without a validated solution. Timed-out models that violate constraints are rejected.
- Installed Z3 5.3.1 crashes with exit 139 for both bit-vector jobs. Their logs and commands are preserved; the cause has not been minimized. A tiny bit-vector Optimize example passes. This is recorded in the project pad (`z3-allocation-oracle-crash`); no `z3-bugs` pad exists. The bit-vector path is excluded from accepted results.

All feasible solver/prototype assignments cited above are rechecked by the Python domain/interference model. The exact baseline, known outer-exit assignment, inner-region solver assignment and whole/enclosing/inner prototype assignments also pass the library's independent `allocation-check/verify` through generated Coil programs compiled with the fixed test compiler. The native verifier executes, but these programs do **not** execute machine code generated from the modified allocation.

## Reproduction

```
python3 docs/benchmarks/frequency-allocation/reproduce.py "$STOGIR_TEST_COIL" \
  build/frequency-reproduction
```

This copies frozen library source `bca7c4d`, replays the captured allocation exactly, runs the solver-free whole-function and inner-region searches, exports complete assignments and executes the library verifier on both. It records compiler, source, trace and tool identities. The workflow completed successfully; `results/reproduction.json` and compressed raw outputs retain its evidence. Z3 is not needed for this command.

For the optional finite-choice oracle, run `choices.py TRACE BASELINE_LOG OUTPUT.json --region 69 --whole-parts --seconds 45`. Region indices are fixture selections for the diagnostic, not compiler optimization rules. Source trace provenance remains in the regional-allocation report.

## Native implementation gate

The next implementation should first preserve the whole-function interval structure: the verified bypass result needs coordinated reassignment of existing children, not additional splits or a solver. Port the bounded ejection-chain search and complete transfer-cost model as an optional post-allocation pass, after control-only inheritance and before final location indexing/callee-save layout.

The bridge must use the real alias and PHI metadata and recognize validated constant/frame-address rematerialization. New spill homes must use each parent's actual `SpillShape` and frame allocator; the offline verifier's synthetic home identities do not validate stack geometry. Fixed and SIMD classes, required uses, lifetime holes and all existing ABI checks remain mandatory. Verify assignments before and after each accepted transaction; rebuild any assignment-derived indexes before emission. Preserve source identity and deterministic tie breaks.

Then add native JIT/AOT regressions for bypass versus body execution, loop-carried values, fixed call arguments/results, spill homes, coalescing/PHIs and register pressure. Inspect the real hot function, build matched fixed-source hosts and measure alternating runtime and generation. Only after that evidence should broader inlining be revisited. Default policy, integration sources, installation and pushed state are unchanged by this experiment.
