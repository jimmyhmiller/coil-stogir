# Coordinated allocation recoloring

This experiment implements and validates coordinated recoloring, but it does not fix the hot zero-trip path or improve measured runtime. The earlier allocation analysis misidentified two rejection edges inside the `k` loop as its zero-trip bypass; the correction below supersedes that interpretation. The bounded search is now also implemented as an optional native post-allocation pass; the compiler workload has not yet been timed with it. There is no new cycle measurement or claim that the 5× generation / 1.10× runtime target is met.

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

The whole-function result also passes a second, direct allocation replay on the original 402 allocation children: 14 register fields change, with no new split, spill home, frame change, live-range edit or constraint edit. Its output exactly matches the modeled assignment. This confirms that the modeled body-path improvement can be implemented by recoloring existing pieces; the model's 1,950 block fragments need not become native allocation pieces. The emitted replay and exact plan are in `results/whole-children*`.

The enclosing-loop case improves these body-path edges (previously misidentified as the handoff’s zero-trip bypass):

| CFG edge | Baseline memory copies | Recolored memory copies |
|---|---:|---:|
| 203 → 19, first body rejection | 5 | 0 |
| 206 → 19, second body rejection | 5 | 0 |
| 61 → 55, shared continuation | 6 | 1 |
| 60 → 61, body return | 0 | 4 |

The remaining continuation copy carries parent 65. These copies disappear on rejection paths within the loop; the actual zero-trip exit is unchanged. Some memory stores counted here may already be eliminated by canonical spill-home logic, so only native disassembly and execution can establish the emitted and dynamic benefit. Full edge changes are retained in `results/enclosing-loop-edge-changes.json`.

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

The next implementation should first preserve the whole-function interval structure: the verified body-path result needs coordinated reassignment of existing children, not additional splits or a solver. Port the bounded ejection-chain search and complete transfer-cost model as an optional post-allocation pass, after control-only inheritance and before final location indexing/callee-save layout.

The bridge must use the real alias and PHI metadata and recognize validated constant/frame-address rematerialization. New spill homes must use each parent's actual `SpillShape` and frame allocator; the offline verifier's synthetic home identities do not validate stack geometry. Fixed and SIMD classes, required uses, lifetime holes and all existing ABI checks remain mandatory. Verify assignments before and after each accepted transaction; rebuild any assignment-derived indexes before emission. Preserve source identity and deterministic tie breaks.

Then add native JIT/AOT regressions for bypass versus body execution, loop-carried values, fixed call arguments/results, spill homes, coalescing/PHIs and register pressure. Inspect the real hot function, build matched fixed-source hosts and measure alternating runtime and generation. Only after that evidence should broader inlining be revisited. Default policy, integration sources, installation and pushed state are unchanged by this experiment.

## Native implementation checkpoint

`allocation-recolor.coil` ports the bounded search over original allocation children. `allocation-transfers.coil` derives the logical copy set from actual schedule/CFG, canonical location indexes and PHI operands, including read-only constant/frame recipes. Whole children keep their ranges and constraints. Domain propagation honors required/fixed uses and physical reservations; search is bounded to depth 3, 100 visits per root, 8 changes and 32 rounds. Each accepted transaction strictly reduces the proxy and passes `allocation-check/verify`. Typed homes are allocated through `frame/spill-slot!`, all sibling home metadata is updated, and the compiler rebuilds its location index before callee-save layout. Errors discard the owned allocation. Static loop weights saturate at depth 6 to bound score arithmetic. The `private/with-recolor` context option defaults off.

The native replay exactly matches the prototype: 14 original-child register changes, no new home, proxy 454,018, edge copies 58 (29 memory), internal copies 16 (8 memory). Reproduce against the current source with `python3 docs/benchmarks/frequency-allocation/native-replay.py "$STOGIR_TEST_COIL" build/frequency-reproduction build/native-recolor-reproduction`.

Focused tests cover coordinated swaps, fixed clobbers, exact lifetime holes, GPR/SIMD masks, required uses, deduplicated copies, constant recipes, invalid endpoints, deterministic convergence and a newly allocated 16-byte aligned spill home. `tests/recolor-native.coil` executes 24 live loop-carried values through both bypass and unknown-call paths, with the option disabled and enabled, checking all outputs across zero/small/larger trip counts and wrapping values. Its emitted object also passes `tests/recolor-native-link.c` linked by Clang. Existing global-forwarding diamond/loop fixtures pass with recoloring enabled. Broad suite, compiler integration, real hot-function disassembly and matched runtime/generation measurements remain outstanding.

### Instruction-phase correction

The initial full-workload candidate rejected `coil.compiler.unit.unit-interface-render` with `odd split boundary needs instruction-specific lowering`. Recoloring had converted an existing spill cut into a register move at a phase where emission only permits a register-to-home store. The fix adds explicit transfer-direction constraints to candidate validation. Coalesced redefinitions are excluded through a shared predicate used by both the cost builder and actual split-move emission, including selected multi-output instructions. Allocation now passes the real matched definition plan to the cost builder. A regression proves that an otherwise cheaper unsupported register move is rejected in favor of the legal assignment. The 24-value JIT pressure fixture still passes. The first broad suite completed 303/305 standalone tests, with only the two previously recorded failures; 73 linked consumers require their separate fixture-aware run. A fresh full suite and workload build follow the correction.

## Measured native result and path correction

Corrected library `01adb66` and integration `8ae701ab` pass FAST, 303/305 standalone tests (only the known `jit-parameter-specialize` and `private-leaf` failures), all 73 linked consumers with 5,410 fresh object fixtures, and the C-linked pressure test. Raw validation is under `native/validation/`. Three alternating workload rounds reproduce the fixed seed object in every run.

| Host | Minimum cycles (B) | Median cycles (B) |
|---|---:|---:|
| LLVM | 42.560 | 42.767 |
| Retained induction | 54.087 | 54.595 |
| Recolor research | 54.043 | 54.835 |

Median recoloring runtime is 0.44% slower than retained and 1.282× LLVM; minimum is essentially equal to retained. Instructions fall by about 0.74%, but there is no reliable cycle gain. Keep the option disabled. One separate serial generation pair takes 9.675 seconds retained versus 303.916 seconds recolored (31.4× slower); this is one pair, not a repeated distribution or a fresh LLVM comparison. Both policy objects exactly match their prior host-build objects; with the option off, baseline object `221639…` remains byte-identical.

A full graph replay now confirms that the compiler bridge produces exactly the allocation-only assignment: 402 original children, 14 changed registers, no new home, cost 503,298→454,018, and successful native object emission. Its baseline and recolored functions match the host instruction counts (336→320), stack-load instructions (29→27), and stack-store instructions (28→24). Thus the lack of gain is not a failure to port the modeled assignment.

**The earlier path interpretation was wrong.** In the fixed source, block 54 is the outer `i` loop, block 55 is the `k` loop over reexports, and block 56 is the inner `j` loop over existing providers. Edges 203→19 and 206→19 reject a target match within a nonempty `k` loop; 61→55 returns to its header. These are not the hot zero-trip path. The actual zero-trip path is 321→55→16→54. Its exit 16→54 still has three memory transfers before and after recoloring, visible as `ldp x25, x23` and `ldr x27` in both emitted functions. The loop-depth proxy rewards changes within the body while leaving the frequently taken zero-trip path unchanged. Captured register assignments remain valid, but they do not demonstrate the handoff’s desired optimization.

The next experiment must first establish an improvement on 16→54 through actual generated code. Candidate mechanisms include region splitting around the body or a rotated guard combined with allocation, using graph-derived frequencies and complete transport legality. Do not promote this pass or merely raise inlining budgets based on the previous bypass claim. Raw runtime/generation results, source identities, disassembly and the full-graph replay are retained in `native/`.

### Rotated-guard combination probe

The captured full graph also emits with existing loop rotation plus recoloring (33 assignment changes, proxy 536,450→477,940). It has 358 static instructions, 35 stack-load instructions and 29 stack-store instructions, versus 320/27/24 for unrotated recoloring. The zero-trip guard at offsets 0x154–0x15c branches to 0x42c; continuing the outer iteration still executes three reloads at 0x440, 0x444 and 0x448. This combination also fails the target code-shape gate. No whole-workload timing or execution result is claimed for the rotated replay. Artifacts and the exact observation are in `native/rotation-probe.json` and `native/graph-rotated*`. Next investigate a body-region allocation with frequency estimates that distinguish the entry guard from loop-carried body work, rather than another global search over unchanged whole children.
