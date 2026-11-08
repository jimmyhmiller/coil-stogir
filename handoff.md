# Coil Stogir performance handoff

Updated November 7, 2026. **Both goals are still unmet.** This document describes where things stand and the plan for meeting them. Earlier session logs are in git history (this file at `171fa16` and before) and in the `coil-stogir` pad.

## November 7 evening (latest)

Library `feature/branch-fusion` at `4b4eda0`; Coil `stogir/branch-fusion` at `1c8c3100` vendors it (quick FAST passes; Stogir-only bootstrap reproduces the seed object). Nothing installed or pushed.

**Status.** Full bootstrap (`bootstrap.py`, with LLVM rows) at `37f4a55`/`79cc79f1`: seed generation **Stogir 7.296 s vs LLVM 36.10 s = 4.95×** (goal 5×; need ≤ ~7.22 s). Runtime: matched hosts ~61.5B vs ~46B cycles (**~1.34×**); the bootstrap's native rows show 8.80 s vs 7.08 s generation work (1.24×). Goal ≤ 1.10×.

**Generation commits (all byte-identical except where noted):** disjoint register reservations from an advancing cursor (`9fe1d77`, −1.7%); pressure scans limited to the value's class mask (`cffc350`); fixed-use event sort by register buckets + merge sort (`1d2814a`); structure verified once in schedule preparation (`41311d9`); SCCP proofs carried into code generation, with owned/image SCCP compacting before final validation so 98% of functions reach the backend with a matching proof (`1824cb9`; compacted templates change inline-budget outcomes, matched hosts same cycles and identical outputs); four-lane content hash (`37f4a55`).

**Bug found and fixed (`4b4eda0`).** `bbd9683` emitted SEXT of a signed load as a 64-bit copy; after a W move of the I32 value (e.g. into a callee-saved register at a split), bits 32-63 were zero. Now the copy is used only in the value's original, unsplit allocation part. sext-load has a regression case. It surfaced through a CSE experiment that changed inlining in `graph.contains?`/`lookup`; found by hash-gated bisection over SCCP graphs and lldb.

**Measured and rejected this evening:** Euler-interval dominance in GCM placement (no gain); single-decode `uses.build` (no gain); multiply by (2^k+1)·2^m as shift-adds, fused into ADD/SUB (neutral to slightly worse on Apple cores: shifted adds are not cheaper than `mul`); global CSE of pure nodes (9% of pure nodes were duplicates, but +0.7B instructions and +0.5B cycles, likely longer live ranges and changed inlining, and +1.5% generation).

**Where the runtime gap is (unbiased `tsprof`, same source).** Functions present in both hosts take *fewer* samples under Stogir (0.89×); the gap is in functions LLVM inlined away (39K of 94K Stogir samples). Call overhead (prologue/epilogue/argument setup) is ~17% of the gap. Stack loads are the largest bucket (+24% of the gap). Of hot stack loads, the biggest class is reads of address-taken stack objects (5,972 samples), larger than spill reloads (3,636) or callee-saved restores (3,182). A clear instance: calls returning `Option`/`Result` in x0/x1 (call-results kind 1) store the pieces into a stack place and immediately reload them (`scratch.bump`). **Next step:** make kind-1 call result pieces SSA values followed by explicit stores to the place, so load forwarding and mem2ssa remove the round trip.

## November 7 afternoon session (superseded by the evening section)

Library `feature/branch-fusion` is now at `73ed968` (plus earlier commits listed below); Coil `stogir/branch-fusion` at `60af4293` vendors it through `5b9fe69`-era work (later library commits are not yet vendored). Nothing installed or pushed.

**Status (matched measurements, same source):** runtime **1.36–1.40×** LLVM by cycles (64.4B vs 46.0B min, from 1.48×); generation **~8.0–8.2 s** in the candidate (from ~8.7 s; goal ≤ ~7.3 s). Every change below keeps the full library suite green (except the two pre-existing failures); output-preserving generation changes were checked to emit byte-identical objects.

**Profiling correction (important).** `pcprof` uses ITIMER_PROF, whose signals macOS delivers on kernel exit, so ~70% of its samples land on page-faulting stores and memmove into fresh pages. Earlier per-instruction conclusions from it (including "memmove is the gap" and "one load in verify.structure") are unreliable. Use `/usr/bin/sample` (call trees) or the new unbiased PC sampler `tsprof` (Coil `build/s8/tsprof.c`: a helper thread suspends the target thread every 200 µs and reads PC/LR). With it, memmove time is about equal between hosts.

**Model of the runtime gap.** Cycles ≈ shared memory stall + instructions ÷ sustained IPC, on both P-cores and E-cores (E-core ratio is the same 1.49×). The gap is dynamic instruction count (Stogir ~256B vs LLVM ~152B now) plus taken branches. Remaining gap by unbiased role samples: loads, compares, register-allocator reloads/moves (~27% of the gap), prologue/epilogue (no shrink-wrapping), extensions.

**Runtime commits this afternoon:** frame slots addressed directly (`2260fe6`); zero stores from XZR (`b80fef5`); narrow truth tests without UXTB (`8845aaf`); ZEXT/SEXT as register views with 64-bit signed loads and LDPSW (`8791284`, `bbd9683`, `<I32 ZEXT>`); pairing-NOP compaction (`a910c2b`); return tails through forwarded empty blocks (`f69a393`); small test blocks emitted in place at ENDs, i.e. loop rotation (`8928a88`, −2.1% cycles); BUILTIN-MOVE copy forwarding (`37a0d6c`, neutral).

**Generation commits:** SWITCH verification without a use index (`66982a1`, `73ed968`); graph compaction before SCCP/backend (`b43c441`, `e8ef92d`, byte-identical, −3%); early-exit pressure scans (`5b9fe69`); content-hash validation proofs (`b24ba1d`, user-approved: skip re-validation only when a 128-bit digest proves the graph identical to one that passed); index loops instead of slice iterators (`6221e7c`, `c571547`); adapter skips template SCCP for adapted graphs over 1.5× the inline budget (Coil, byte-identical, −2%).

**Rejected/measured:** inline budget 1024 (−1% cycles, +18.5% generation); skipping SCCP's final validation when cleanup changed nothing (almost never applies); TRUNC coalescing (neutral, kept).

**Next ideas, ranked:** spill splitting around rare calls in loops (e.g. closure-subprogram-scoped reloads six values per iteration); shrink-wrapping prologues; IR-level integer narrowing (i32 counters as U64 containers + TRUNC/SEXT); constant hoisting out of loops; signed div/rem by powers of two with known-nonnegative dividends; for generation, a monotone-cursor reservation query in register pressure and sharing use lists across backend stages.

## The goals

For the whole Coil compiler bootstrap:

1. **Generation:** Stogir IR-to-machine generation at least **5× faster than LLVM O3**. It is measured in the fixed LLVM-built candidate while it emits the compiler; frontend time is excluded.
2. **Runtime:** the Stogir-built compiler runs within **10% of the LLVM-O3-built compiler** doing the same work (each emits the current compiler with Stogir O3).

Correctness, JIT and AOT, and the pinned upstream architecture must be preserved. Do not disable verification, remove checks, special-case workloads, overwrite the global compiler, or run `build full` or comprehensive workflows while iterating.

## Where things stand

Two full bootstraps at Coil `5c751f13` (results in Coil `docs/benchmarks/branch-fusion/bootstrap-run-{1,2}.json`). Every generated host reproduces the exact seed Stogir object.

| Measure | Run 1 | Run 2 | Goal |
|---|---:|---:|---:|
| Generation, Stogir / LLVM | 9.64 / 36.96 s (**3.83×**) | 8.73 / 36.55 s (**4.19×**) | ≥ 5× (≤ ~7.3 s) |
| Runtime cycles, Stogir / LLVM | 74.26B / 50.15B (**1.48×**) | 73.92B / 50.97B (**1.45×**) | ≤ 1.10× (≤ ~56B) |
| Runtime wall | 22.51 / 15.13 s | 23.02 / 15.53 s | |

History: 1.65× runtime and 3.40× generation at `68ced91e`; 1.56× and 3.39× at the start of November 7. About **24% fewer runtime cycles** and **20% less generation time** are still needed.

The workload moves. Generation improvements in the library also make the compiler being run cheaper, for both hosts. During this session the remaining runtime work got relatively harder for Stogir (1.43× → 1.46×) while absolute cycles fell. Always compare the two hosts on the same source.

## Where everything is

All paths are under `/Users/jimmyhmiller/Documents/Code/projects`. Everything is committed; **nothing is installed or pushed.**

| Item | Location |
|---|---|
| Coil integration | `coil/.worktrees/stogir-branch-fusion`, branch `stogir/branch-fusion` (on `stogir/copy-forwarding`) |
| Stogir library | `coil-stogir/.worktrees/branch-fusion`, branch `feature/branch-fusion` at `342ffb7` (on `feature/guard-trip-first` `03d2b10`); vendored unchanged into Coil `src/compiler/stogir/stogir/` |
| Candidate build seed | `build/seed-bin/coil` in the Coil worktree (symlink to the `stogir-static-entry-allocations` candidate) |
| Fixed library test compiler | `coil/.worktrees/stogir-allocator-choice-fusion/build/bin/coil-candidate` |
| Measurement tools | Coil `docs/benchmarks/branch-fusion/tools/` (see its README) |
| Profilers | Coil `docs/benchmarks/cir-copy-forwarding/tools/` (`pcprof`, `memprof`) |
| Scratch knobs (not for merging) | `coil/.worktrees/stogir-budget2` (`scratch/inline-budget-2`: layout cutoff), `stogir-bulk-limit` (`scratch/bulk-limit`: inliner rejection reasons), `stogir-inline-budget` (`experiment/stogir-inline-budget`: inline budget and LLVM pipeline knobs), `stogir-genbase` (detached base used for one generation A/B; safe to remove) |

Validation at the current heads:
- The full library suite (342 tests) passes except `jit-parameter-specialize` and `private-leaf`, which also fail on `03d2b10`, before this work.
- The `aot-*-link` tests need link flags from earlier JIT tests; `aot-switch-link` was run by hand and passes.
- Quick FAST passes and the whole bootstrap reproduces the seed object.
- **Full FAST has not been run;** it is required before pushing.

Commits made on November 7:
- Library: `3860588`, `ca6be1e`, `5766b5c`, `ea4453e`, `c7d8a4a`, `dee6e58`, `342ffb7`.
- Coil: `33622239`, `079a8d80`, `c76981cd`, `803d81a0`, `c702d2e2`, `49e738fb`, `f16d787b`, `5c751f13`, `d550c17c`.

## How to measure (read this first)

- **Runtime changes need matched hosts.** A backend change also changes the work each generated host does, so `native-stogir` bootstrap rows from two candidates are not comparable. Build both hosts from the same source with the old and the new candidate (`mkhost.sh`), then alternate them (`ab.py`); it checks that the outputs are identical.
- **Generation changes:** `genab.py ROOT N base=OLD new=NEW` alternates candidates on the same source, compares IR-codegen time and reports whether the emitted objects are identical. An identical object means a pure generation change.
- **Compare cycles, not retired instructions.** Apple cores fuse compare-and-branch and decode 8 wide. Cutting 2–5% of instructions (CBZ fusion, Boolean folds) moved cycles by 0–2%. Every large runtime win this session removed *taken branches* with almost no instruction change.
- Host load on this machine is often 10–50 (other sessions, `rustc`). Use at least three alternating rounds and compare minimum and median. Single bootstrap runs vary by about 5%.
- `bootstrap.py --stogir-only` skips the LLVM rows for faster correctness checks. The official numbers need the full run.
- Profiles: `/usr/bin/sample PID 30 1 -file F`, with the PID of the process you launched (`cmd & P=$!`), then `incl.py` and `children.py` for inclusive shares. PC sampling (`pcprof`) gives self time only, and LLVM's inlining moves samples into callers, so per-function cross-backend comparisons can mislead.
- Per-event hardware counters are not available headless: `kperf` needs root, and `xctrace` CPU Counters fails to connect to DTServiceHub. Cache-miss and branch-miss data would settle several open questions (below) if they can be collected interactively.

## What we know

**Runtime.**
- With inlining off on both sides, LLVM takes 119.5B cycles and Stogir 185.0B. LLVM still inlines `alwaysinline` trait wrappers, so this overstates Stogir's per-body gap, but per-body code quality matters at least as much as inlining.
- Raising Stogir's inline budget does not help: 1024 gave +19% generation with no cycle gain, 2048 gave +51%. Inlined code is not cleaned up. In a replay of `verify.structure`, full inlining raised instructions 31.3B → 37.3B with no cycle change.
- Inliner gate, whole compile: 129,585 calls to registered templates, 60,975 inlined. Rejections: exhausted per-caller budget (dominant), never-inline targets, callees containing indirect calls (about 30K checks; for example the `KeyOps` eq/hash function-pointer wrappers and allocator `dyn` calls), and callees larger than the remaining budget.
- Copies: about 93M `memmove` calls / 11.2 GB, against LLVM's 58M / 7.1 GB. LLVM expands copies up to about 256 bytes inline (with q-register `ldp`/`stp`) and its interposer counts miss those, so the true LLVM copy volume is unknown.
  - The clearest missing optimization is a field read of a by-value struct through `get`, such as `(.name (get list i))` on a 176-byte struct: Stogir 88.3M cycles against LLVM's 40.7M in an isolated benchmark.
  - Raising the inline-copy cap to 256 bytes gives 54.7M there, but a global cap is neutral to worse on the whole compiler, because real copies (for example `box-expr` into the heap) get slower.
- The largest single function gap is `stogir.verify.structure`: 5–9× in context against 2.3× in a warm isolated replay. Most of its samples sit on one load in the outer loop. It is unexplained without hardware counters; cold memory, register pressure and limited memory-level parallelism are the suspects. The loop uses all ten callee-saved registers and still spills about 26 times, and both arms of inlined `contains?`/`borrow-node` are computed before the branch (early placement).
- The remaining unconditional branches (static count, current host):
  - 107K, against LLVM's 44K;
  - about 68K follow PHI moves, which is partly unavoidable;
  - 61K are backward;
  - 11K are dead `b` after `brk`;
  - jumps into jumps are down from 29.7K to 53.
- Register allocator choice barely matters for LLVM (basic instead of greedy costs it 2.6%), and the prologue/epilogue share of samples is under 1%.

**Generation** (call-tree profile of the candidate emitting the compiler; shares of the whole emit run, of which generation is about 55%):
- Image pipeline about 25%: register allocation 7.9% (`allocation.pressure-state-into!` is 43% of that), CFG and schedule preparation 5.4%, emission 3.2%.
- SCCP 13.4%, of which `sccp-rewrite.validate` is 6.4%.
- Module finish 10.9%; template preparation 7.4%; inline expansion 7.1%; `mem2ssa` 4.1% (`cfg.build` is 22% of that); copy forwarding 4% before this session's fix.
- Verification as a whole is about 12% of generation.
- SCCP is not exactly idempotent: a second run on its own output changes the emitted object. Skipping it nevertheless had no runtime cost.

## What changed on November 7 (matched A/B results)

| Change | Effect |
|---|---|
| Boolean integer-view folds and IF/COND condition canonicalization; CBZ/CBNZ; STP/LDP frame saves (lib `3860588`) | Instructions −2.1%, cycles within noise |
| Scalar `def` reads become constants on the CIR path (Coil `079a8d80`) | With the above: instructions −5.6%, cycles about −2% |
| Direct switch dispatch, no stubs on empty edges (lib `ca6be1e`) | Cycles −3.4% minimum, −5.1% median |
| PHI-only blocks count as empty (lib `ca6be1e`) | Cycles −3.5% minimum |
| Taken-edge moves at IF projection entry (lib `5766b5c`) | Cycles −1.2% minimum, −1.8% median |
| In-place return at return tails (lib `5766b5c`) | Cycles −1.7% minimum, −1.9% median |
| LDP/STP pairing of adjacent accesses (lib `ea4453e`) | Cycles −1.2% minimum, −0.5% median |
| Owned SCCP; skip the image's entry SCCP on graphs that are already SCCP output (lib `c7d8a4a`, Coil `49e738fb`) | Generation −7.5%; runtime unchanged |
| Reuse the vectorizer's CFG/schedule preparation (lib `dee6e58`) | Generation −3.5%, identical objects |
| Bulk array initialization (Coil `5c751f13`, lib `342ffb7`) | Generation −2.9% (copy forwarding), instructions −2.1% more (library) |

**Measured and rejected; do not repeat without a new idea:**
- Bigger inline budgets.
- A global 256- or 512-byte inline-copy cap.
- Expanding only copies into local stack slots: 55% slower on the field-read benchmark.
- If-converting cheap pure diamonds into COND: cycles +0.7–2.3%. Branches here are well predicted and COND lowering is expensive.
- Switch fallthrough for the case laid out next: neutral.
- Branchless DEF/REF test in the verify loop.
- Bottom-up layout for functions over 257 blocks: neutral.
- The CIR-level inliner from the previous session (`d25c60b8`).

## Plan to meet the goals

The two goals pull against each other: most runtime work adds generation work. Budget each runtime change against its generation cost with `genab.py`, and fund it with algorithmic generation savings.

### Runtime: about 24% of cycles to find

Ranked by expected value given the evidence above. Estimates are uncertain; measure each with matched hosts.

1. **Copy elimination after inlining (scalar replacement of aggregates).** This is the biggest known gap shape and the main thing LLVM has that Stogir lacks.
   - **Mechanism.** Keep fixed-size copies as a graph-level operation until after inlining and SCCP, instead of lowering them to `memmove` or 8-byte pairs when the adapter builds the graph. Load forwarding and dead-store elimination can then read through a copy and delete the temporary, and the copies that survive are lowered late: inline `ldp`/`stp` (q registers) up to about 256 bytes, `memmove` above.
   - **Work involved.** A new opcode carried through verify, use lists, scheduling, alias/effect analysis, inliner eligibility and lowering.
   - **Expected size.** The `get`-field benchmark suggests large local wins; whole-compiler value is unmeasured.
2. **More taken-branch removal in layout and emission.** This lever has worked five times.
   - **Candidates.**
     - Pick the fallthrough predecessor of a merge by edge weight or loop depth.
     - Tail-duplicate small merge blocks beyond return tails.
     - Rotate every loop shape so the back edge is a conditional branch.
     - Keep dead `b` after `brk` out of hot code.
   - **First step.** Classify the 61K backward branches in hot functions.
3. **Register pressure from early placement.** Sink pure values computed before a branch but used in only one arm into that arm (late placement after inlining). In `borrow-node`/`contains?` the negative-index path is computed on the positive path. This should reduce spills in hot loops such as `verify.structure`.
4. **Inliner eligibility, not budget.** About 30K rejections are callees with indirect calls. Constant function pointers, such as `KeyOps` hash/eq loaded from a known table, could become direct calls before eligibility is decided, which also makes them inlinable.
5. **Smaller items**, each likely 0.5–2%:
   - fuse COND's comparison into `cmp`+`csel` (x86 upstream has `COND_CMP_INT`);
   - fold a Var-static cell's address (three dependent loads become one);
   - address module-local symbols directly in AOT (`adrp`+`add` instead of loading an address slot);
   - hoist or rematerialize loop-invariant constants instead of rebuilding `movz`/`movk` every iteration;
   - drop redundant extensions (`sxtb` after `ldrsb`, `ubfx #0, #32` chains).
6. **Get hardware counters for `verify.structure` and the top ten hot functions** (cache and branch misses) if root or interactive Instruments is possible. That would tell whether the in-context 5–9× is memory behavior or code shape.

### Generation: about 20% of time to find

1. **Cheaper verification without checking less** (about 12% of generation).
   - `integer-operations-target-structured` and `structure`: per-operand helper calls and repeated classification.
   - `switch/verify`: rebuilds a full use index per graph when any SWITCH exists.
   - `calls/verify`: repeated full scans.
   - Same checks, same independence; just faster.
2. **Register allocation pressure queries** (about 6% of generation). `pressure-state-into!` loops over every register and every range of the interval with reserved-range lookups. Maintain free-until and next-use incrementally, as upstream's linear scan does with its active and inactive sets.
3. **Stop rebuilding analyses on unchanged graphs.**
   - `cfg.build` inside `mem2ssa` when the CFG is known.
   - `uses/build` in `inspect-verified-site`, once per call site.
   - `uses/build` in SCCP `finish!` and the verifiers.
   - The use and CFG facts are often available from the previous pass.
4. **Remaining whole-graph copies.**
   - `sccp-rewrite` duplicates its input only to diff old against new in `seed-iteration!`; record changed references during the rewrite instead.
   - `own-definition!` copies each template into module memory. Optimize directly into the module allocator or move ownership.
5. **Fewer full SCCP runs.**
   - Templates run SCCP in preparation and again in module finish after expansion; callers run it before inlining.
   - The image's entry SCCP is now skipped for clean graphs. Extend that to multi-return templates, which need canonicalization that preserves the fixpoint, and to callers with no expansion.

**On reusing validation results.** About half of validation re-checks a graph that was already checked, so reusing the result is tempting, but the two main cases differ:
- **The inliner's caller check** really is redundant today: SCCP validated that exact graph and only the root list changes afterwards. But the library's contract says only its own internal path may vouch for that, and a later change that edits the graph in between would silently leave it unchecked. Estimated saving about 2–4% of generation.
- **The post-rewrite check inside SCCP** is *not* redundant: the final check sees the graph only after the iterative folder has changed it. Skipping it would lose detection and localization of rewrite bugs.

Recommendation: keep validation as it is and pursue item 1 first.

### Before calling anything done

Repeated full bootstraps (same source, controlled load) must meet both targets, with every host reproducing the seed object. Then run full FAST, live emission and the full library suite including the `aot-*-link` tests. Install and push only after that, deliberately, and report committed, installed and pushed states separately.

## Reference: testing workflow

### Library changes

Develop in the library worktree and test with the fixed test compiler, so changing the library never changes the compiler that builds its tests:

```sh
STOGIR_TEST_COIL=/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-allocator-choice-fusion/build/bin/coil-candidate
cd /Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/branch-fusion
COIL_LIBRARY_STATE=0 "$STOGIR_TEST_COIL" run tests/jit-branch.coil --backend stogir -O3 --no-debug --debug-checks
# whole suite (about 25 minutes, 6 in parallel):
.../coil/.worktrees/stogir-branch-fusion/docs/benchmarks/branch-fusion/tools/libtests.sh $PWD /path/to/out
```

- **Don't edit library source while the suite runs;** it compiles each test from the live tree.
- New behavior gets a test that fails on the previous library. Check this by copying the test into a scratch copy of the previous library's `src`.

### Real-graph replays

`COIL_TPDE_STATS=1 COIL_TPDE_SERIAL=1 COIL_STOGIR_GRAPH=<function> <candidate> build <file>` prints a lossless `stogir-snapshot` of one function's graph. The `benchmarks/*/generate.py` scripts turn a snapshot into a replay program (see `benchmarks/phi-home-entry`). `emit-obj` does not print snapshots; use `build`.

### Integrating into Coil

1. Copy changed library files into Coil `src/compiler/stogir/stogir/` (they must stay identical: `diff -rq`).
2. Append a provenance paragraph to `src/compiler/stogir/README.md`; never replace it.
3. Rebuild the candidate after every source change, README included: the toolchain stamp covers it, and `bootstrap.py` asserts it.

```sh
cd /Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-branch-fusion
PATH="$PWD/build/seed-bin:$PATH" COIL_LIBRARY_STATE=0 python3 scripts/dev.py build candidate
COIL_LIBRARY_STATE=0 python3 scripts/dev.py test fast --compiler build/bin/coil-candidate --quick
python3 docs/benchmarks/private-call-module/bootstrap.py --compiler build/bin/coil-candidate --output build/<fresh-dir> [--stogir-only]
```

A candidate builds in about 15 seconds and a Stogir-only bootstrap takes about 70 seconds. Every generated host must reproduce the exact seed object. The bootstrap must run from the worktree root with `COIL_*` cleared, which the script does.

### Repository rules

- The root library checkout has user-owned, untracked `docs/benchmarks/results/`: do not modify, stage or delete it. Stage named files.
- New worktrees go under each project's ignored `.worktrees`.
- Keep central upstream credit in LICENSE, NOTICE and PROVENANCE; no SPDX headers.
- Stubs must fail loudly.
- Report confirmed Coil bugs in the `coil-bugs` pad.
- Commit on non-default branches only.
