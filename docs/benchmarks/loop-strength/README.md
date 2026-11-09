# Loop address strength reduction — runtime research

The new optional `loop-strength` pass replaces affine products inside natural loops with loop-carried values. It recognizes one external entry and one natural back edge in either predecessor order. The original induction step can add or subtract any entry-invariant word value. Supported affine expressions use ordinary 32/64-bit ADD, SUB, MUL by an invariant operand, constant SHL and representation-preserving views. Their initial value and per-iteration difference are evaluated outside the loop; a new PHI advances by that difference.

Correctness uses modular arithmetic at the original width, without assuming signed overflow cannot occur. Memory/control operations, loop tests and roots retain their identities. The body may branch, call, store, exit early or contain nested loops. Invariant availability is proved at the entry edge with dominance and natural-loop membership. Other PHIs, nonlinear products, width changes, hard-copy barriers, loop-varying steps and multiple back edges decline. Explicit worklists avoid recursion proportional to expression depth. Analyses are rebuilt after each successful batch; the caller's graph remains untouched.

Constant field offsets and representation views share a recurrence for their common base, leaving normal memory-address folding intact. No function names, source references, physical registers or measured profile weights enter the policy. The target context exposes `with-strength`; it is disabled by default. O3 applies the pass after loop rotation/load hoisting, then SCCP cleanup before vectorization and final scheduling.

## Validation

`tests/loop-strength.coil` passes 72 arithmetic fixtures, with 107,520 original/transformed native executions against an independent wider arithmetic model. It also asserts disappearance of scheduled loop multiplies, idempotence, graph ownership and conservative declines, including a valid multiple-latch graph. `tests/loop-strength-native.coil` verifies nested address recurrences through calls and stores, two exits, field-offset sharing and null zero-trip cases. Both the manual rewrite and the integrated O3 path pass 292 native calls each. The C-linked consumer passes 122 cases with full array-state checks. See `validation/results.json` for commands and scope. Full library/linked suites and final acceptance gates have not been rerun.

## Captured compiler graph

`replay.py` restores any single lossless snapshot and emits four diagnostic objects. Using the previously captured `src-mod-lookup-at` graph (`../induction-ranges/lookup.trace.gz`), text sizes are:

| Configuration | Bytes |
|---|---:|
| Regional control | 308 |
| + strength reduction | 296 |
| + load hoisting | 308 |
| + load hoisting + strength reduction | 288 |

The combined object's loop advances its pointer with `add #40`; the previous `mov #40; mul; add` chain is gone. Field offsets remain direct loads. A register copy remains before the first field load. This snapshot is a code-shape diagnostic, not a runtime benchmark and not the fully inlined host. Disassemblies and snapshot identity are under `lookup/`.

The first full compiler integration and runtime comparison are below. The target remains ≥5× LLVM generation speed and ≤1.10× LLVM runtime on the fixed workload. The retained small-regional control is 1.27347× LLVM in runtime-a; the combined hoisting/strength result is mixed against that control. No runtime policy is promoted. Nothing installed or pushed.


## First whole-compiler comparison (COPY-based rewrite)

Library `2342f7e`, integration `9f823d82`, preserved generator `58ed76cb…`. Three serial alternating rounds; all 15 objects match the fixed seed. All task-owned preparation was terminal before timing. LLVM's first sample was unusually slow (46.229B versus 42.677B and 42.572B); it is retained.

| Host | Min cycles (B) | Median cycles (B) | Median / LLVM | Median instructions (B) |
|---|---:|---:|---:|---:|
| llvm | 42.572 | 42.677 | 1.0000 | 139.688 |
| regional | 53.860 | 54.347 | 1.2735 | 206.635 |
| hoist | 54.248 | 54.392 | 1.2745 | 205.788 |
| strength | 54.345 | 54.590 | 1.2792 | 210.933 |
| hoist-strength | 54.062 | 54.111 | 1.2679 | 210.042 |

Strength reduction alone regresses the regional control by 0.447% median / 0.900% minimum. Hoisting plus strength is mixed against regional: −0.434% median but +0.375% minimum. It is modestly faster than hoisting alone, but does not establish a win against the retained best control. Its median instruction count increases by about 3.4B. No option is promoted from this comparison. The runtime target remains unmet, and generation speed is not newly measured; overlapping build durations are preparation only.

The disabled control exactly reproduces `edef6c97…`. Both new hosts pass separate fixed-seed checks; the actual compiler lookup loop has no multiply. Quick FAST passes with strength/hoisting/rotation/regional enabled (48.5s). The complete source/vendor identity held for the measured generator.

## Direct-PHI follow-up and remaining address view

A follow-up replaces each original expression directly with its recurrence PHI instead of appending a PHI and retaining a COPY. It keeps reference identities while removing unnecessary intermediate graph nodes. Expanded arithmetic, integrated nested JIT and C-linked tests pass. However, the captured combined object's bytes are identical: the surviving register move was not caused by the introduced COPY. No runtime benefit is claimed for this follow-up.

An isolated diagnostic copy of the compiler pipeline dumps the graph after strength/SCCP. It shows a word PHI feeding a BITCAST to ADDR, which feeds the first field LOAD. Existing address matching only absorbs the view when it also finds ADD arithmetic. The planned general follow-up is zero-offset selection through a full-width address view, with explicit matched uses and retirement before liveness. The diagnostic copy is under `build/loop-strength/inspect`; production contains no diagnostic hook.


## Zero-offset full-width address views

The normal persistent matcher now has a fallback for word-to-address views when neither immediate nor indexed arithmetic addressing applies. It selects the underlying word as a zero-offset address, records that exact operand before liveness, and retires only views whose actual uses were all absorbed. Shared/rooted views and COPY barriers remain. Bounded partial chains retain their selected intermediate base. Floating reinterpretations are excluded; zero-extension remains an explicit definition. Arithmetic/indexed modes keep priority. This is a general matching rule, enabled with normal fusion; only the strength pass is optional.

The expanded address suite passes, including 30 new native view fixtures (120 executions), fuse-disabled controls, rooted/escaping values, COPY before/after the view, long chains, and width-conversion checks. Existing offset/indexed/pressure tests, named/nested addresses, integrated nested strength execution and the freshly linked C consumer pass. Replacing only the matcher with pre-change `6423076` in an isolated copy makes the new selected-base assertion fail as expected; the helper API remains available so this is a behavioral negative control, not a missing-symbol failure.

The captured combined loop now loads directly from its carried pointer. Its text is 284 bytes versus 288 before the rule; the other three captured variants remain unchanged. Evidence is under `address-views/`. No new full-workload runtime result exists for this matching follow-up yet. The next comparison needs freshly generated controls because the general matcher change also affects configurations with strength disabled.


## Follow-up compiler preparation

Library `da3e6b0` / integration `4473e86e` includes the direct-PHI rewrite and zero-offset address views. Preserved generator SHA-256 `8282cf7083fdc784ca48e560e54080e76295d730495306776798ac98f85f4716` is under integration `build/loop-strength/views/`. The candidate rebuilt successfully and the vendored library matches. Fresh `regional`, `hoist`, `strength` and `hoist-strength` hosts and quick FAST are preparing there. These overlapping builds are not controlled generation measurements.

Once all jobs are terminal, verify each new host's fixed-seed output and compare six hosts serially for three alternating rounds: fixed LLVM, previous regional (`build/loop-strength/control/bin/coil`), and all four new `views/` hosts. Use the existing `docs/benchmarks/deferred-loop-splits/compare.py` with a fresh output directory and require `9d775276…` for every output. Preserve the previous generator and hosts. This preparation is not a completed follow-up runtime result.


## Direct-PHI and address-view whole-workload comparison

All four fresh hosts passed separate fixed-seed checks; quick FAST passed (48.6s, concurrent preparation only). All 18 timed outputs also match the fixed seed. Three serial alternating rounds completed with no task-owned build/test overlap. The first LLVM sample was again slower (44.465B); all samples are retained.

| Host | Min cycles (B) | Median cycles (B) | Median / LLVM | Median instructions (B) |
|---|---:|---:|---:|---:|
| llvm | 42.820 | 42.861 | 1.0000 | 139.652 |
| old-regional | 54.017 | 54.355 | 1.2682 | 206.629 |
| regional | 53.932 | 54.261 | 1.2660 | 206.480 |
| hoist | 54.159 | 54.175 | 1.2640 | 205.544 |
| strength | 54.396 | 54.454 | 1.2705 | 210.024 |
| hoist-strength | 53.964 | 54.014 | 1.2602 | 208.823 |

regional versus old-regional: median -0.174%, minimum -0.157%.

strength versus regional: median +0.355%, minimum +0.859%.

hoist-strength versus regional: median -0.455%, minimum +0.058%.

The combined pass remains mixed against the fresh regional control; no runtime option is promoted. It still executes about 2.34B extra instructions. The address-view change removes roughly 0.15B instructions in the no-strength control, with minimum and median cycles both about 0.16–0.17% lower in this comparison; this small change needs a repeat before claiming a reliable runtime benefit. The runtime ratio remains around 1.26× LLVM, outside 1.10×. No controlled generation measurement was added. Runtime-first research continues with a fresh dynamic profile; see `../runtime-profile/README.md`.
