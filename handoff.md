# Coil Stogir performance handoff

Updated November 6, 2026. The performance goal is **paused and unmet**. This document describes the state at the pause; it does not resume development or benchmarking.

## Goal and current evidence

For the whole Coil compiler bootstrap:

- IR-to-machine-code generation must be at least **5× faster than LLVM O3**. The user explicitly excluded frontend time from this compile-time target.
- The resulting Stogir-built compiler must run within **10% of the LLVM-O3-built compiler**.
- Preserve correctness, JIT and AOT, and the pinned upstream architecture. Small benchmarks are diagnostic tools, not substitutes for the whole-compiler goal.

Latest **completed**, matched whole-bootstrap diagnostic:

| Measurement | LLVM O3 | Stogir O3 | Required Stogir |
|---|---:|---:|---:|
| IR-to-machine generation | 37.110109 s | 10.925092 s | ≤7.422022 s |
| Generated compiler runtime, wall | 17.157830 s | 28.315133 s | ≤18.873613 s |

That is **3.396778× faster generation and 1.650275× runtime**. At that checkpoint we need approximately **32.1% less generation time and 33.3% less runtime**. These are single diagnostic runs, not repeated acceptance medians.

Source/candidate: Coil `68ced91e`; whole evidence: `131d3115`. Results are in the Coil worktree at `docs/benchmarks/contained-fields-and-bit-identities/bootstrap/results.json`.

**Important interpretation:** generation compares one fixed host emitting the compiler with each target backend. Runtime compares the resulting native compiler executables doing the **same work**: each emits the current compiler using Stogir O3. It does not compare an LLVM host doing LLVM optimization against a Stogir host doing a different backend's work.

## Where to work

All paths below are under `/Users/jimmyhmiller/Documents/Code`.

| Item | Path / checkpoint |
|---|---|
| Standalone library repository | `projects/coil-stogir` |
| Coil repository | `projects/coil` |
| Pinned upstream reference | `open-source/ir`, commit `92171d0a4a36b0acf707f2dea7998de615dd4acd` |
| Latest library implementation | `projects/coil-stogir/.worktrees/spill-home-edges`, commit `4e068bc` |
| Latest Coil integration | `projects/coil/.worktrees/stogir-spill-home-edges`, source/candidate `a831fb94` |
| Latest component evidence / pause report | Same Coil worktree, commits `5daecd7e` / `be78c1d8` |
| Retained comparison baseline | `projects/coil/.worktrees/stogir-contained-field-promotion`, evidence HEAD `131d3115`, candidate built from `68ced91e` |
| Fixed standalone test compiler | `projects/coil/.worktrees/stogir-allocator-choice-fusion/build/bin/coil-candidate` |
| Candidate build seed | `projects/coil/.worktrees/stogir-static-entry-allocations/build/bin/coil-candidate` |
| Common emitter caller object | `projects/coil/.worktrees/stogir-class-register-choice/build/class-choice-comparison/emitter/runner.o` |

Do not assume either repository's main checkout contains the latest experiment. The named worktrees and their committed evidence are the checkpoints. Latest experimental worktrees were clean at the pause. These experiments are **committed, not globally installed, and not pushed**.

Recorded binary identities: latest Coil candidate SHA-256 `aa49a61a577946e3c95541f7ceceaaecd2c0ddf0e0b424dbec7085e272e3e27b`; standalone test compiler SHA-256 `69773cb09fe6ef00fd91aca8a6580d9d1b967db1f980fd314a1350af48547ed3`. Check identities before relying on an existing binary; a worktree's current HEAD alone does not identify its previously built candidate.

Local navigation: [latest component/pause report](../coil/.worktrees/stogir-spill-home-edges/docs/benchmarks/spill-home-edges/README.md), [completed whole results](../coil/.worktrees/stogir-spill-home-edges/docs/benchmarks/contained-fields-and-bit-identities/bootstrap/results.json), [historical broad profile](../coil/.worktrees/stogir-spill-home-edges/docs/benchmarks/verified-operands-bootstrap/profile/summary.json), [latest standalone validation](.worktrees/spill-home-edges/docs/validation/spill-home-edges/README.md). These links depend on the local worktrees remaining present.

The root library checkout has user-owned, untracked `docs/benchmarks/results/`. **Do not modify, stage or delete that directory.** Stage named files rather than using `git add .`.

Create new worktrees under each project's ignored `.worktrees`. Develop and validate on this Mac; use `computer.jimmyhmiller.com` over SSH only for specifically Linux-required work. Preserve centralized upstream credit in LICENSE/NOTICE/PROVENANCE; do not add SPDX headers throughout the source and tests.

Project Pads: `coil-stogir/index`, `coil-stogir/paused-wrap-up`, `coil-stogir/current-goal-status`, and `coil-stogir/spill-home-edges-development`. The Coil index also links the paused report. Report confirmed external Coil bugs in `coil-bugs`, following its instructions; do not silently work around them.

## What the latest change actually does

The latest work completes part of the shared spill-home protocol. Definitions can establish a private parent's home, making later stores of the same value redundant. Earlier experiments removed contiguous split-boundary stores but **left ordinary CFG edge stores intact**. The provider's mismatch paths still stored those values and then reloaded them.

`a64/spill-homes.coil` now supplies a certificate only when all relevant machine definitions, coalesced values, widths and private frame slots can be established. Resolution owns that certificate; the emission view borrows it until resolution is released. Empty-block/layout checks and actual edge lowering see the same view.

Only **ordinary same-parent register-to-that-exact-home stores** are suppressed. Phi moves and literals are added afterward and retain their behavior: they can establish a new incoming value. Reloads are unchanged. Frame/scope introspection, external/computed entry and incomplete-definition cases retain the original fallback.

Actual provider body, with exact agreement between standalone graph replay and Coil object:

- Baseline: 1,464 bytes, SHA-256 `97dcf1a1c7350db51fb2fd7a688a85a0f380f2487565dcd42180d9a4fa9c505d`.
- Complete home/edge protocol: 1,324 bytes, SHA-256 `fb1e094e38633bfe2d4e840267236516c25b28eaeebe3293b10fcb42508ffb9e`.

Latest component results, eight alternating CPU samples after excluded warmup:

| Workload | Retained Stogir | New Stogir | LLVM before | LLVM after |
|---|---:|---:|---:|---:|
| Actual provider | 99.8375 ms | 89.9860 ms | 51.0495 ms | 51.1475 ms |
| Actual emitter | 621.7595 ms | 618.3710 ms | 356.2935 ms | 354.6925 ms |

The provider improved **9.87%**. Emitter performance is effectively neutral, with similar movement in its LLVM control. Both LLVM object pairs are identical; expected execution results pass. Host activity qualifies the timings. This has **not yet demonstrated a whole-compiler improvement**.

Evidence: Coil `docs/benchmarks/spill-home-edges/README.md`, per-component `results.json`, generation transcripts, process snapshots and compressed disassembly. Standalone correctness evidence: library worktree `docs/validation/spill-home-edges/`.

## How I have been testing

### 1. Keep the implementation and emitter under test separate

Use a fixed compiler to compile standalone library tests, so changing the library does not silently change the compiler that builds the test. Run from the library experiment's worktree, whose `Coil.toml` resolves its own `src`.

```sh
STOGIR_TEST_COIL=/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-allocator-choice-fusion/build/bin/coil-candidate
cd /Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/spill-home-edges

COIL_LIBRARY_STATE=0 "$STOGIR_TEST_COIL" run tests/spill-home-loop.coil \
  --backend stogir -O3 --no-debug --debug-checks

COIL_LIBRARY_STATE=0 "$STOGIR_TEST_COIL" run tests/spill-home-loop.coil \
  --backend llvm -O1 --no-debug --debug-checks --sanitize=address
```

The sanitizer flag is `--sanitize=address`. Debug checks stay enabled in correctness runs. Performance measurements use their documented O3/no-debug configuration instead.

The expanded spill-home test checks **432 native answers across O1/O2/O3**, including 24 invariants used before and after a call, a native target that destroys caller GPRs/NZCV, alternating call/bypass paths with Phi joins, and frame-address fallback. It also passes ASAN.

Additional native suites used here: `jit-pressure`, `jit-call-pressure`, `jit-phi-call-redefinition`, `jit-floating-pressure`, `jit-phi`, `jit-loop`, `jit-switch-pressure`, `jit-bulk-pressure`, `private-call-allocation`, `jit-loop-guard`, and `frame-memory`. Four ASAN suites passed: the expanded home loop, Phi-call redefinition, floating pressure and loop behavior. Tests check semantics and ABI behavior; static instruction counts alone do not establish correctness or speed.

Before editing Coil, read `coil guide`. For damaged delimiters use `coil balance --write` and inspect the changes; do not run a formatter over unrelated code.

### 2. Reduce real compiler graphs and compare actual emitted code

The provider replay is generated from a lossless captured graph, rather than a hand-written approximation:

```sh
python3 benchmarks/spill-home-availability/generate.py
COIL_LIBRARY_STATE=0 "$STOGIR_TEST_COIL" run \
  build/spill-home-availability/replay.coil \
  --backend stogir -O3 --no-debug --debug-checks
```

The generator defaults to the compressed snapshot in `docs/validation/spill-home-availability/snapshot.txt.gz`. Its inspection tail records definitions, owners, ranges, transfers, loop depths, frame layout and machine bytes. The latest version asserts eight definition-writeback positions and the 1,324-byte body. The ASAN replay emits the same body. A temporary edge-certificate bypass failed the real body assertion with exit 134; the source was restored afterward. The failure was not an API/build error.

For architecture-sensitive decisions, extract the pinned upstream C rule and compare decisions. Example: the separate split-child ranking experiment matched **625 native ranking decisions** from an unchanged C fragment compiled with UBSAN. That proves the tested ranking rule, not the whole allocator. Inputs that would overflow signed C scoring were excluded explicitly; no upstream reachable bug was established.

### 3. Integrate into Coil, then build one candidate

Vendor source under `src/compiler/stogir/stogir/`. Preserve Coil's existing vendor provenance and append the new commit/qualification; do not replace its provenance file wholesale. Freeze **all** compiler/stdlib source, including vendored validation docs, before building or timing: the toolchain SDK digest includes those files.

The latest worktree already has `build/seed-bin/coil` pointing to the fixed build seed listed above:

```sh
cd /Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-spill-home-edges
PATH="$PWD/build/seed-bin:$PATH" COIL_LIBRARY_STATE=0 \
  python3 scripts/dev.py build candidate

COIL_LIBRARY_STATE=0 python3 scripts/dev.py test fast \
  --compiler build/bin/coil-candidate --quick
COIL_LIBRARY_STATE=0 python3 scripts/tests/stogir-live-emission.py \
  build/bin/coil-candidate
```

Latest build and live-emission/prebuilt retention checks passed. Quick passed in **79.1 seconds**, over its 60-second target under host activity. Read the report, not merely the outer script's exit code. Full FAST with the required normal environment remains required before pushing compiler changes. Do not run `build full` or comprehensive/release workflows while iterating, and do not overwrite the global compiler with experiments.

### 4. Measure small real workloads with fixed opaque callers

Only start these after builds, tests and profiles are terminal. Run the two measurements serially:

```sh
STOGIR_BASELINE=/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-contained-field-promotion/build/bin/coil-candidate
STOGIR_CALLER=/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-class-register-choice/build/class-choice-comparison/emitter/runner.o

python3 docs/benchmarks/frontend-providers/measure.py \
  --compiler "$PWD/build/bin/coil-candidate" \
  --baseline "$STOGIR_BASELINE" --output build/handoff-provider-run

python3 docs/benchmarks/private-call-module/measure.py \
  --candidate "$PWD/build/bin/coil-candidate" \
  --baseline "$STOGIR_BASELINE" --caller-object "$STOGIR_CALLER" \
  --output build/handoff-emitter-run
```

Use fresh output directories. Scripts disable library state, request serial native codegen and record phase telemetry. Each compiles the **same current source** with old/new Stogir and LLVM controls, verifies execution, excludes a warmup, then takes eight samples with alternating forward/reverse order.

- Provider: 256 modules, 8 facades, 20,000 queries alternating present/missing names. The C caller owns opaque inputs; construction/destruction are outside its process-CPU kernel timer. The independently computed expected count is 100,000.
- Emitter: `docs/benchmarks/class-register-choice/emitter/kernel.coil`, linked to one unchanged opaque caller object. Its runtime metric is child-process CPU time, including process overhead; it is not the provider's internal timer. Exact answers are compared across variants. That differential agreement is not an independent correctness proof, so keep the semantic library tests too.
- Each script takes **one generation sample** per variant. Those samples are diagnostic, not reliable compile-speed medians.

Record compiler/fixture/caller/object hashes, source/SDK identity and host process inventories before/after. Verify LLVM control object pairs really are identical. Compare paired current-source results; never claim an improvement by comparing LLVM numbers from different source checkpoints. Preserve raw samples and disassembly. A smaller body can still be slower.

### 5. Periodically test the whole compiler

After useful small evidence, with frozen source and no overlapping jobs:

```sh
python3 docs/benchmarks/private-call-module/bootstrap.py \
  --compiler "$PWD/build/bin/coil-candidate" \
  --baseline "$STOGIR_BASELINE" \
  --output build/handoff-whole-bootstrap
```

The driver serially emits Stogir and LLVM compiler objects using the fixed candidate, plus a same-source previous-Stogir object. It links each into a **private** toolchain prefix. Each generated compiler then emits the same current main program using Stogir O3. All outputs must reproduce the exact seed Stogir object. It records wall/CPU/RSS, generation phase sums, compiler/object/SDK hashes and host activity. This is a diagnostic, not final acceptance: repeat matched runs under controlled load for acceptance.

The paused run lives in `build/spill-edges-bootstrap`. Only seed-Stogir completed: 10.962724 s generation / 19.391906 s whole emit. LLVM was interrupted. Partial progress/pause records are committed under `docs/benchmarks/spill-home-edges/paused-bootstrap/`. **There is no new complete comparison.** Do not use the partial LLVM object or partial row as a result.

The driver's `--resume` reads `results.json`, not `progress.json`. Do not blindly pass `--resume` to this interrupted run: a safe resume needs explicit checkpoint/artifact verification or a fresh output directory. No benchmark process was left running at the pause. Poll exact live process/session handles; an observation timeout is not termination.

## Where I think the largest runtime gains are

These are priorities, not promised speedups.

1. **Complete register/spill availability and CFG resolution.** This has the strongest recent concrete evidence: applying the home proof to ordinary edges gained 9.87% on a real provider. Remaining work includes per-use/predecessor reload availability and spilled-Phi handling. Current code still reloads and reconciles locations without upstream's complete availability model. Inspect the actual hot paths; do not add another store-placement cost heuristic.
2. **Improve the generated code for broad compiler hot paths, especially graph verification, emission and aggregate/access loops.** The current emitter is about 1.74× LLVM in the component run. Historical profiles show substantial verification, repeated use-list/operand work, memory copying, resolver/provider work and allocation APIs. Existing aggregate promotion, private-call effects, checked field reads, operand-read proofs and bounded inlining have already addressed parts of this. Re-profile and inspect current native bodies before extending them; do not repeat an already-completed optimization or raise inline budgets blindly.
3. **Finish the phase/use contract before further split-placement changes.** Upstream has LOAD/USE/DEF/SAVE positions. We currently have two phases, and a use at an interval split belongs to a different side than it does in upstream's inside-range split. General odd reloads are intentionally rejected. Remaining free-assignment/reload-restart split categories need correct transfer lowering and ownership, not simply earlier numeric cuts.

Do not equate upstream parity with guaranteed target performance. The implementation still needs measured machine-quality improvements on the whole compiler. Avoid workload-specific names, special cases, unchecked access or disabling verification to obtain a benchmark result.

## Biggest compile-time costs: evidence and limits

There are two different questions: time spent running the generated compiler, and the fixed host's IR-to-machine generation cost. A generated-compiler profile helps identify runtime gaps, but it is **not** an exact decomposition of the current 10.925092-second generation measurement.

The most useful saved broader profile is Coil `docs/benchmarks/verified-operands-bootstrap/profile/summary.json` (source `ca35b006`, evidence `9c946167`). It predates several later fixes. Both native compiler hosts were separately profiled while compiling the same program; their output objects matched the seed. Stogir worker had 21,159 samples; LLVM worker 12,088. Main-thread join waits were excluded.

| Inclusive family, share of sampled worker | Stogir-built host | LLVM-built host |
|---|---:|---:|
| Native per-function compilation/emission | 31.7% | 31.9% |
| Graph verification | 12.8% | 8.7% |
| Allocation APIs / scratch-related calls | 7.6% | 8.1% |
| Use-list construction | 4.2% | 5.7% |
| Register allocation | 4.9% | 4.4% |
| Module preparation | 8.5% | 8.0% |

Module finalization was visible at 9.6% in the Stogir host; its missing LLVM family label is not zero cost. `sccp.optimize-memory` was also a large inclusive stack: 5,056 / 21,159 Stogir samples and 2,520 / 12,088 LLVM samples. It nests within compilation; **do not add these percentages together**. Inlining changes symbol visibility, so leaf-name counts are not direct cross-backend speed ratios.

My compile-time priority is therefore **broad optimization/graph processing and module preparation/finalization**, followed by repeated verification, use reconstruction and memory traffic. Fresh profiles should distinguish unavoidable semantic work from repeated graph copies, redundant scans and analysis rebuilding. Keep proof and diagnostic equivalence when reusing validated facts; do not remove checks.

Register-pressure queries were a serious older bottleneck and already received fixed-use events, physical reservation indexing, assigned-interval indexing and reusable scratch. An isolated emitter once showed roughly 24% allocation samples, but a later whole-bootstrap profile showed only about 4.6–4.9%. **Do not keep tuning the allocator based on the old synthetic percentage.** Likewise, old linear location lookup and repeated opcode classification profiles describe costs that have already been partly addressed.

The exact current pass-by-pass split of the 10.925092-second generation budget has not been freshly measured after the latest fixes. That is a measurement task still open, not a reason to invent percentages. The latest edge change established no generation gain: single provider samples 0.964939→0.972538 s; emitter 2.674535→2.675337 s.

For profiling, use a separate untimed run and the actual linked native compiler hosts. Saved helpers/raw samples are under `verified-operands-bootstrap/profile/`; an older reproducible example is `return-allocation-bootstrap/profile-profile.py`. Inspect/adapt their expected SDK/result paths before running. Do not profile alongside timing runs, count main-thread `__ulock_wait` as optimizer CPU, or optimize sampled telemetry `write` calls as application work. Fresh host activity invalidated earlier generation comparisons; preserve those exclusions.

## Failed and neutral experiments worth knowing about

| Experiment | Result | State |
|---|---|---|
| Uniform homes without ordinary-edge suppression | Provider +14.4% runtime | Rejected, isolated; library `3509fb3`, Coil evidence `89628a89` |
| Loop-depth-costed homes, still without edge suppression | Provider +3.9% runtime | Rejected, isolated; library `418a6cd`, Coil evidence `58baec22` |
| Split-child blocked-register scoring | Provider/emitter neutral; noisy generation samples discarded | Isolated; library `e316eac`, Coil evidence `38cfc365`; **not included** in latest home-edge branch |
| Contained fields / literal identities | Emitter component −2.63%, whole runtime essentially unchanged | Included in retained baseline; demonstrates why micro gains need whole checks |

The latest edge fix explains a missing piece of the previous policies, but does not invalidate their measured regressions. Do not merge every experimental branch together or promote neutral work as a performance gain. Preserve central attribution and the exact pinned upstream reference when porting rules.

## Recommended next steps when the user resumes

1. Finish a fresh or safely verified resumed whole comparison for `a831fb94`. Check exact output equality from every generated host before interpreting speed.
2. Obtain a fresh, separate profile of the current fixed emitter and generated hosts. Use it to rank runtime and generation work independently.
3. Continue reload availability / memory-Phi resolution against reduced real graphs, preserving parallel copies, frame ownership, ABI clobbers and fallbacks. Complete the phase/use adaptation before enabling remaining split categories.
4. After each change: native/ASAN semantics, actual emitted-body inspection, paired small measurements, then whole diagnostics only when warranted. Reject regressions promptly.
5. Only claim completion after repeated whole-bootstrap results meet both original targets and required validation passes. Deliberately integrate/install/push afterward; report committed, installed and pushed states separately.

The goal remains paused. No performance target was redefined or marked complete in preparing this handoff.
