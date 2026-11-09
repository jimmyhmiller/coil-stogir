# Loop address strength reduction — runtime research

The new optional `loop-strength` pass replaces affine products inside natural loops with loop-carried values. It recognizes one external entry and one natural back edge in either predecessor order. The original induction step can add or subtract any entry-invariant word value. Supported affine expressions use ordinary 32/64-bit ADD, SUB, MUL by an invariant operand, constant SHL and representation-preserving views. Their initial value and per-iteration difference are evaluated outside the loop; a new PHI advances by that difference.

Correctness uses modular arithmetic at the original width, without assuming signed overflow cannot occur. Memory/control operations, loop tests and roots retain their identities. The body may branch, call, store, exit early or contain nested loops. Invariant availability is proved at the entry edge with dominance and natural-loop membership. Other PHIs, nonlinear products, width changes, hard-copy barriers, loop-varying steps and multiple back edges decline. Explicit worklists avoid recursion proportional to expression depth. Analyses are rebuilt after each successful batch; the caller's graph remains untouched.

Constant field offsets and representation views share a recurrence for their common base, leaving normal memory-address folding intact. No function names, source references, physical registers or measured profile weights enter the policy. The target context exposes `with-strength`; it is disabled by default. O3 applies the pass after loop rotation/load hoisting, then SCCP cleanup before vectorization and final scheduling.

## Validation

`tests/loop-strength.coil` passes 72 arithmetic fixtures, with 13,440 original/transformed native executions against an independent wider arithmetic model. It also asserts disappearance of scheduled loop multiplies, idempotence, graph ownership and conservative declines, including a valid multiple-latch graph. `tests/loop-strength-native.coil` verifies nested address recurrences through calls and stores, two exits, field-offset sharing and null zero-trip cases. Both the manual rewrite and the integrated O3 path pass 292 native calls each. The C-linked consumer passes 122 cases with full array-state checks. See `validation/results.json` for commands and scope. Full library/linked suites and final acceptance gates have not been rerun.

## Captured compiler graph

`replay.py` restores any single lossless snapshot and emits four diagnostic objects. Using the previously captured `src-mod-lookup-at` graph (`../induction-ranges/lookup.trace.gz`), text sizes are:

| Configuration | Bytes |
|---|---:|
| Regional control | 308 |
| + strength reduction | 296 |
| + load hoisting | 308 |
| + load hoisting + strength reduction | 288 |

The combined object's loop advances its pointer with `add #40`; the previous `mov #40; mul; add` chain is gone. Field offsets remain direct loads. A register copy remains before the first field load. This snapshot is a code-shape diagnostic, not a runtime benchmark and not the fully inlined host. Disassemblies and snapshot identity are under `lookup/`.

Full compiler integration and matched runtime comparison are next. The target remains ≥5× LLVM generation speed and ≤1.10× LLVM runtime on the fixed workload. The last accepted comparison is still 1.27471× LLVM runtime; this implementation does not establish an improvement yet. Nothing installed or pushed.
