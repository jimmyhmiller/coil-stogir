# Coil Stogir performance handoff

Updated November 11, 2026: an x86-64 Linux backend was added (first section below). AArch64 status, from November 8, 2026 (night): **The generation goal is met at the default settings (5.09–5.31×); the runtime goal is not: ~1.31× at default, ~1.29× with the best options, which cost generation (~4.3–4.5×).** The section below is self-contained and supersedes the earlier ones for runtime work; older sections are kept for history. Earlier session logs are in git history and in the `coil-stogir` pad.

## November 10-11: x86-64 Linux backend (latest for x86)

Stogir now has an x86-64 backend (`src/stogir/x64`, System V, ELF, Linux JIT), and the Coil compiler builds itself with it on x86-64 Linux. The AArch64 numbers and sections below are unchanged by this work: AArch64 objects are byte-identical before and after.

### Status against the goals on x86-64 Linux (Ryzen AI Max+ 395, LLVM 21)

| Goal | Stogir | LLVM | Ratio | Bar |
|---|---:|---:|---:|---|
| Generation wall | 1.097 s | 9.50 s | 8.7x faster | >= 5x, met |
| Runtime, cycles | 106.74B | 92.35B | 1.156x | <= 1.10x, not met |

Runtime instructions are 1.48x. The profile points at the x64 register allocator: spill stores and reloads around loop back edges, with only 12 general registers allocatable (r10, r11 and rbp are reserved). The list of known tuning gaps and the rounds so far are in Coil `docs/benchmarks/x86/tuning.md`.

### What is verified

- Linux: `-O3` self-build, bootstrap reproduces the seed object, identical objects across thread settings, 2400 of 2400 parallel compiles identical, ThreadSanitizer self-emit clean, correctness sweep against LLVM output (demos 138/138, stdlib 24/24, examples 30/30, library tests 1053/1056).
- Library: 426 tests pass on the Mac (the three that fail, `x64-host`, `x64-jit-image`, `x64-jit-text`, execute x86-64 code and need that host); on Linux all `tests/x64-*.coil` pass (`x64-call-*` through `tools/x86/call-tests.sh`).
- Known Linux failures: `jit-hva-incoming`, `jit-hva-outgoing` (Coil compiler SSEUP limitation), `jit-hva-abi` (AArch64 convention), `jit-floating-extension` (FMA needs an image under bare text). No x86-64 SHIMCALL program has run end to end through the compiler.

### Where everything is

- Design and decisions: `docs/X86_PORT.md`, `docs/X86_FAMILIES.md`, `docs/ABI.md`, `docs/ARCHITECTURE.md` ("A compile call only reads its graph"), `tests/X64_STATUS.md`.
- Linux test runners: `tools/x86/remote-test.sh`, `tools/x86/call-tests.sh`, `tools/x86/family-tests.sh`.
- Coil integration: branch `stogir/x86` in the coil repository (vendors this library at ded7635; measurement tools and the defect reports 001-004, all fixed, under `docs/benchmarks/x86/`).
- Parked: branch `x86/tune-wip` (one unbuilt, unmeasured allocator-option change; not for merging as is).
- Large table-shaped tests are written as data with `src/stogir/test-data.coil` (`table`, `link-entries`).

## November 8 night: exact instruction comparison and the 10% push (latest)

This session had one directive: reach runtime ≤ 1.10× LLVM at any generation cost. It did not get there. What it did produce is an **exact, per-instruction comparison of the two hosts**. That turns "where is the gap" from guesswork into measurement, plus three new options and a ranked plan. Start here.

### Status against the goals

Matched hosts emit the Coil compiler at `coil/.worktrees/stogir-branch-fusion` (the workload root, "R" below) with Stogir O3. The LLVM host is `R/build/n8-full8/host-llvm/bin/coil`, at about 42.2–42.5B cycles min; the goal is ≤ ~46.5–48B.

| Configuration | Runtime cycles vs LLVM | Generation vs LLVM |
|---|---:|---:|
| Default | ~1.31× | 5.09–5.31× (met) |
| `BASE` = `COIL_STOGIR_INLINE=small=80,small-scope=any,hoist=1 COIL_STOGIR_LOOP_EVICT=1 COIL_STOGIR_LOOP_RELOAD=1` | ~1.29–1.30× | ~4.3–4.5× (+18%, measured in hp12/hp15) |
| `BASE` + `COIL_STOGIR_PREDICT=1` | ~1.28–1.29× | +0.5% more |
| Profile-guided layout (diagnostic bound only, see below) | ~1.25× | — |

Runtime numbers moved by about 1% between rounds; host load was often 10–30. Always compare within one alternating round.

### Where everything is

Paths are under `/Users/jimmyhmiller/Documents/Code/projects`. Nothing is installed or pushed.

| Item | Location |
|---|---|
| Stogir library | `coil-stogir/.worktrees/inline-policy`, branch `feature/inline-policy`. This session: `f6d21fa` call holes, `c08cd47` static branch prediction, `015b4a1` loop rotation (on top of `9ff761d` loop evict/reload, `b8766f8` prune default, `261c3cd` hoist frames, shrink-wrap and inline-policy commits). |
| Coil integration | `coil/.worktrees/stogir-inline-policy`, branch `stogir/inline-policy`, `0ef1e351` vendors the library unchanged into `src/compiler/stogir/stogir/` and adds the env flags. |
| Option flags (adapter `codegen_stogir.coil`) | `COIL_STOGIR_INLINE=...` (policy: `budget`, `template`, `small`, `small-scope=any\|loop`, `leaf`, `hoist`, `always`, `pair`, `indirect`), `COIL_STOGIR_SHRINK_WRAP`, `COIL_STOGIR_PRUNE_DEFAULT`, `COIL_STOGIR_LOOP_RELOAD`, `COIL_STOGIR_LOOP_EVICT`, `COIL_STOGIR_CALL_HOLES`, `COIL_STOGIR_PREDICT`, `COIL_STOGIR_ROTATE`. All are off by default, and the default object is unchanged (`9d775276…`). |
| Results and README | Coil `docs/benchmarks/inline-policy/README.md` (all rounds, against the goals) and `results/ab-*.log` |
| Host builders and A/B | Coil `docs/benchmarks/inline-policy/tools/`: `mkhost-env.sh ROOT CANDIDATE OUTDIR [COIL_STOGIR_*=…]` (prints generation seconds); `ab.sh ROUNDS OUTDIR name=host …` (alternates hosts, prints min/median cycles relative to the first host, checks that all outputs are identical); `genenv.py` (generation) |
| Exact-count tooling | Coil `docs/benchmarks/inline-policy/tools/bbcount/` (copied from the scratch worktree, see below) |
| Scratch instrumentation worktree | `coil/.worktrees/stogir-ra-audit`, branch `scratch/stogir-ra-audit` (not for merging). Holds the block-counter emitter, frame-audit dumps, `COIL_STOGIR_DUMP=fn` graph dumps and the profile-layout hack. **Its latest changes are uncommitted**; a copy is in `tools/bbcount/ra-audit-uncommitted.patch`. Its `build/` holds the counted hosts (`bb-base`, `bb-default`, `bb-big3`, `bbp-pred2`, `bbp-pgo`, …) and `build/llbb/` (the counted LLVM host). |
| Tests added | Library `tests/branch-predict.coil`, `tests/loop-rotate.coil`; `tests/loop-entry-split.coil` gained `hole-check`. These and `block-layout`, `switch-prune-default`, `shrink-wrap`, `module-execution`, `pressure-index`, `a64-allocate`, `private-call-allocation` pass. **The full library suite and FAST have not been run** for this session's commits. |

### How the exact counts work (reuse this)

**Stogir host.** In the scratch worktree, `COIL_STOGIR_BBCOUNT=1` makes `a64/block-count.coil` emit `movz/movk x16 = 0x500000000000 + 8*i; ldr x17,[x16]; add x17,#1; str x17,[x16]` at every block label. It also prints `bbmap FUNCTION BLOCKREF INDEX` to stdout, which `mkhost-env.sh` captures in `emit.out`. `bbcount.dylib` (`cc -dynamiclib bbcount.c -o bbcount.dylib`) maps the counter array at that fixed address and writes `$BBCOUNT_OUT` at exit.
```
cd coil/.worktrees/stogir-ra-audit
env $(env | grep ^COIL_ | sed 's/=.*//;s/^/-u /') PATH="$PWD/build/seed-bin:$PATH" COIL_LIBRARY_STATE=0 python3 scripts/dev.py build candidate
zsh $INLINE_POLICY/docs/benchmarks/inline-policy/tools/mkhost-env.sh $R build/bin/coil-candidate build/bb-X COIL_STOGIR_BBCOUNT=1 <settings>
(cd $R; COIL_LIBRARY_STATE=0 COIL_TPDE_SERIAL=1 DYLD_INSERT_LIBRARIES=$A/build/bbcount/bbcount.dylib BBCOUNT_OUT=$A/build/bb-X/counts.bin \
   $A/build/bb-X/bin/coil emit-obj src/compiler/main.coil --backend stogir -O3 --no-debug -o $A/build/bb-X/self.o)
objdump -d --no-show-raw-insn build/bb-X/bin/coil > build/bb-X/coil.dis
python3 tools/bbcount/mixdump.py build/bb-X/coil.dis build/bb-X/counts.bin build/bb-X/mix.json
```
Check that `self.o` hashes to the same object as an uninstrumented host. Do not wrap the run in `/usr/bin/time`, which strips `DYLD_INSERT_LIBRARIES` under SIP.

**LLVM host.** Rebuild it from IR with the same counter:
```
cd $R; build/bin/coil-candidate emit-ir src/compiler/main.coil -O3 --no-debug > main.ll
opt -passes='default<O3>' main.ll -o opt.bc && llvm-dis opt.bc -o opt.ll
python3 tools/bbcount/llvm-instr.py opt.ll inst.ll   # side-effecting inline asm, clobbers x16/x17
llc -O3 -mcpu=generic -relocation-model=pic -filetype=obj inst.ll -o inst.o
# link exactly like R/build/n8-full8/llvm-link-command.json
```
The uninstrumented rebuild (`llc` on `opt.bc`) reproduces the real LLVM host: 139.8B vs 139.9B instructions, same output object. Caveats:
- llc duplicates some counter blocks (tail duplication). `mixdump.py` splits those counts across the copies.
- Machine blocks llc creates itself (switch trees, edge splits) carry no counter. `mixdump.py` does not charge code after an unconditional `b`/`br`/`ret`, so LLVM is slightly undercounted, and both sides lose about 20B against the hardware totals.
- `udf` words are inline jump tables, never charged.

**Analysis scripts** (`tools/bbcount/`; all take `DIS COUNTS`, see each docstring):

| Script | What it gives |
|---|---|
| `mixdump.py` → `cmpmix.py`, `fncmp.py` | Per-function, per-opcode mix |
| `fold.py`, `foldrole.py` | Folds Stogir-only functions (callees LLVM inlined) into their callers by dynamic call-site counts, for a per-function gap |
| `annot.py DIS COUNTS FN MIN` | One function's disassembly with exact counts; the best way to compare a hot loop side by side |
| `taken.py`, `takenfn.py` | Taken-branch lower bounds |
| `checks.py` | Branches that lead only to a trap |
| `bigram.py`, `ngram.py`, `ngcmp.py` | Instruction-shape n-grams |
| `stackcls.py`, `stackcls2.py` | Stack loads and stores by frame-slot kind; needs the scratch build's `FRAME`/`SLOT` dump lines in `emit.out` |
| `redload.py`, `redstore.py`, `chains.py`, `swchain.py` | Redundancy and compare-chain counts |
| `mkprofile.py`, `predeval.py`, `scratch-layout.py` | Profile-layout experiment and static-prediction evaluation |

### What the comparison shows

Counted code, `BASE` vs LLVM O3:

| | Stogir | LLVM |
|---|---:|---:|
| Instructions | 191.0B | 118.1B |
| Basic blocks executed | 43.2B | 25.0B |
| Taken branches (lower bound) | 20.0B | 8.8B |
| All loads, incl. stack (accesses) | 41.7B | 28.5B |
| Stack loads: spill reloads / callee-saved restores / locals | 8.3 / 5.2 / 3.4B | ~7B total |
| Spill stores | 3.2B | — |
| Conditional branches that only reach a trap | 3.19B | 0.10B |
| Register moves | 12.5B | 5.0B |
| Extensions (`sxtw`/`uxtw`/`ubfx`/…) | 4.6B | 0.5B |

What these numbers mean:
- **Where the gap lives.** In functions both binaries define, Stogir executes 119.5B vs LLVM's 114.8B, and LLVM's figure includes what it inlined. The rest, 71.5B, is Stogir executing callees that LLVM inlined away.
- **It is spread out.** Folded per function, everything is 1.3–2.9× (top: `primitive-bind-one!`/`primitive-providers-in` +4.8B, `exports-check` +2.6B, `verify.structure` +2.1B, `src-mod-lookup-at` +2.0B, `sccp.optimize-proven-compacting` +2.0B). The top 60 functions hold 55B of the 73B gap. There is no single hot spot.
- **Higher IPC doesn't save Stogir.** Stogir runs at IPC ~3.8 vs ~3.3, because its extra instructions are cheap ones. Cycles track memory round trips and taken branches far more than instruction count.

**The single biggest item: `coil.compiler.resolve.primitive-providers-in`.** It runs 300M outer iterations with an inner `for k` loop that is almost never entered (306M header tests, 6.6M bodies).
- Stogir runs about 49 instructions per iteration, LLVM about 28. Stogir's version accounts for **2.4B of the 8.3B spill reloads**.
- Why: linear scan's "evict the farthest next use" rule evicts the outer values, at the point where the inner-loop values begin, for registers the inner body needs across its calls. It then reloads them in the inner loop's exit block, on every outer iteration (4 reloads at default, 9 with `LOOP_EVICT`).
- LLVM instead keeps the outer values in callee-saved registers, stores the inner values at their definition, and reloads them only inside the rare body.
- The same loop also has an AVec walk with redundant bounds checks (`i<0`, `i>=len`, and `idx&31 < 32`), `sub/asr/lsl` instead of `and`, `mov #240; mul; add` instead of `umaddl`, and a duplicated spill store.

Other measured classes:
- **Checks.** 3.2B trap-check branches plus their compares (~6.4B instructions). LLVM removes them with range facts (IV ≥ 0, dominating `i < len` after load CSE, known bits of masks).
- **Loops.** LLVM hoists invariant loads (`len`, `.data`) and strength-reduces `i*stride`, mostly after loop rotation. Example: `src-mod-lookup-at`, 283M iterations, 11 instructions and 3 loads in Stogir vs ~6 instructions and 1 load in LLVM. Its hot path has no stores.
- **Peepholes.** `cmp x,#0; b.eq/b.lt/b.ge` (3B) could be `cbz`/`tbnz`, but compare+branch fuse, so the cycle value is small. Others: `mov #imm; mul` (1.7B), `(x asr k) lsl k` (0.9B), `ldr x; uxtb`, `mov w; sxtw`, i32 loop counters sign-extended every iteration, and chained `ubfx`.
- **Control flow.** Same-target compare chains a `ccmp` could merge: 1.6B blocks. Linear compare chains on one register (`match` dispatch): 0.76B blocks. LLVM emits 1.55B `csel`-type instructions, Stogir 0.12B.
- **Inlining.** More inlining today makes things worse. The big3 config removes ~4B of call overhead but adds ~9B of spill, frame and branch code. With `primitive-providers-in` inlined into `primitive-bind-one!`, the pair costs 22.2B vs 15.0B out of line; LLVM's inlined version is 10.2B. **Inlining only pays once the allocator handles large functions.**

### What was tried this session (min cycles vs that round's base)

| Change | Result |
|---|---|
| `COIL_STOGIR_CALL_HOLES=1`: a value stays in a caller-saved register and is stored only across a call's clobber (`allocation.call-hole!`) | `primitive-providers-in` 13.7 → 12.5B instructions, but +0.7B (default) / +1.3B (`BASE`) overall. Net loss; leave off. |
| `COIL_STOGIR_PREDICT=1`: Ball-Larus heuristics combined Dempster-Shafer (loop branch, opcode/pointer, loop header, call, return, backward cold propagation to `UNREACHABLE`) feed `IF` arm percentages to the existing Pettis-Hansen layout | −0.5% to −0.9% cycles, +0.5% generation. Taken branches 20.0B → 17.9B. Keep. |
| Profile-guided layout (scratch; measured counts fed into layout) | −3.5% to −3.9% cycles; taken 14.1B. **This is the ceiling for layout work.** Not shippable (LLVM is not PGO). |
| `COIL_STOGIR_ROTATE=1`: `stogir.loop-rotate`, LoopRotate-style header duplication into a guard and the latch, with exact SSA repair, root remapping and no re-rotation | Correct (identical self-compiled object) but neutral (−0.7% min / +0.9% median, +1B instructions), +31% generation from one full re-preparation per rotated loop. Does not fix the `primitive-providers-in` reloads, because the inner values' live ranges still start before the new guard. |
| Rotate + call holes, with or without evict | +2% to +4%. Worse. |

### Ranked plan to reach 1.10× (≈ 11% of cycles still to find)

1. **A frequency-aware allocator, estimated 3–6%.** This is the largest lever and it gates inlining. Linear scan with next-use eviction (pinned `ir_ra.c`) cannot express LLVM greedy's decisions:
   - region splitting at block boundaries chosen by edge frequency;
   - spill weights from use frequency;
   - spilling the short hot value rather than the long cold one.
   It needs block frequencies before allocation (the static predictor in `block-layout.coil`, `predict!`, can be reused) plus a split-around-the-conflict-region eviction (spill the evicted value only for the conflict, not until its next use). Validate on `primitive-providers-in` with `annot.py`: the target is no stack traffic on the zero-trip path.
2. **Loop optimizations on rotated loops, estimated 3–5%.**
   - Hoist invariant loads out of loops with no aliasing writes on paths to the back edge; the rotated guard makes this safe.
   - Forward redundant loads across blocks.
   - Eliminate checks with range facts: IV ranges, dominating conditions, known bits.
   - Strength-reduce `i*stride` addressing.
   - Make rotation cheap (one analysis, innermost-first) before relying on it; the current +31% comes from re-running `pipeline/prepare` per loop.
3. **Inlining, after 1 and 2.** 71.5B of the gap is in callees LLVM inlined. Re-run the big configs (`budget=4096,template=2048,small=256,…`) once spills in large functions are fixed.
4. **Layout and if-conversion, up to ~3%.** Better static heuristics (the profile bound is −3.5%), `csel` if-conversion, `ccmp` chains, switch lowering.
5. **Peepholes, ~1%.** `madd`/`umaddl`, mask `and`, `cbz`/`tbnz`, `ldrb`, deduplicated spill stores, IV widening.

Expect generation to land well below 5× (perhaps ~3×) if all of this is done naively; budget each item with `genenv.py`.

### Pitfalls hit this session

- **Root lists contain control nodes.** The adapter's observed roots include `END`/`LOOP_END` nodes. A graph pass that deletes control must remap roots, or scheduling fails with "live node lacks placement".
- **Dead PHIs are not scheduled** but still reference their merge. When replacing a merge, retarget them, or `register-live` fails with "phi region must be MERGE or LOOP_BEGIN".
- **Re-rotating a rotated loop peels an iteration.** A pass that rewrites loop headers must not revisit headers it created.
- **Coil `at` returns a reference.** `(p/cast i64 (at s 0))` reads the byte; use `(data s)` for a slice's pointer.
- **A Coil helper named `set!` shadows the built-in.**
- **Shell removals.** `rm -rf $VAR/...` is blocked by the session's safety check; use `"${VAR:?}"` or literal paths.
- **IR dumps.** In the scratch worktree, `COIL_STOGIR_DUMP=<function name>` prints `stogir.dump/graph` before native compile. Module functions are named with their module prefix (e.g. `t5.count-hits`).


## November 8 early morning

Library `feature/branch-fusion` at `4589058`; Coil `stogir/branch-fusion` at `892641a2` vendors it (quick FAST passes at every vendoring; every bootstrap host reproduces the seed object; full library suite at `b7d5d00` shows only the two pre-existing failures plus link-flag tests). Nothing installed or pushed. Full FAST has not been run.

**Generation goal: met.** Whole bootstraps (Coil `docs/benchmarks/branch-fusion/bootstrap-run-*.json`): `59e44c0e` 5.09× and 5.25×; `d1efe960` **5.31×** (6.734 s vs 35.751 s). One run at `d1efe960` under host load measured 4.54× (`bootstrap-run-5-loaded.json`, LLVM also slow); repeat any run taken at load above ~10. Margin is a few percent: anything that adds generation work must be paid for.

**Runtime goal: not met.** Matched hosts ~57.3B vs ~43.7B cycles (~1.31×); bootstrap native rows 1.29–1.37× wall depending on load. From 1.39× (60.65B vs 43.67B) at the start of this session.

**Runtime commits (matched hosts):**
- `68d4d0c` loop-entry split for values crossing a call in a loop: cycles −1.8% min / −2.4% median.
- `40d3f6b` zero-count shifts emit as source; `c295be4` nested constant field offsets fold into one address; Coil marks memcmp/bcmp/memchr/strlen/strcmp/strncmp PURE_FUNC: together instructions −3.2%, cycles −1.5% min.
- `8287af0` spill homes in functions with stack scopes: cycles −0.6/−0.8%.
- `c5f9979` XZR zero sources, CSET booleans returned unextended; `196a155` native tail jumps get no frame record (indirect target in a reserved x15); `b789424` frame record stored/reloaded with SP writeback. Each cuts instructions (−0.2% to −0.85%) with cycles within noise.

**Generation commits (identical objects unless noted):** `ae86cab` range intersection from the query position (−1.1/−1.4%); `fb7c6e9` `register-proven!` skips re-validating proven callee content (adapter passes each definition's digest; −1.4/−2.6%); `2883e06` and `ed893f6` graph/opcode/type accessors `:inline (Always)` (−1.3% to −2.5%, −0.5/−1.1%); `cb9d1c2` faster `uses/build` (−0.4/−1.0%); `765ca29` emission borrows the schedule's use lists (−0.2/−0.5%).

**Reverted or rejected (library branches kept):**
- Small-callee inlining at loop call sites (`b7d5d00`, reverted in `4589058`): **cycles −1.5% min / −2.6% median, instructions −1.8%, but generation +2.5%**, which put bootstraps at 5.01× and 4.89×. The unrestricted version (`experiment/small-callee-inline`) was −2.1/−2.5% cycles for +6.4% generation. Re-apply `b7d5d00` (and the adapter's budget clamp at zero) once generation has ~3% margin.
- `experiment/extension-compare-on-fusion` (neutral, +1.2% gen); `experiment/loop-memory` (load forwarding/hoisting across no-write loops: −0.24% ins, +3.8% gen); `experiment/indirect-inline` (neutral; with pair results +15% gen); inline budget 1024 (−0.6% cycles, +19% gen); compaction micro-tuning (no effect).
- Observation: instruction-count cuts alone rarely move cycles on these cores. Cycle wins came from the allocator (loop-entry splits, spill homes) and from fewer memory operations.

**Where the runtime gap is now.** By role: non-stack loads +27% of the gap, frame code +21%, register moves +15%, spill reloads +11%, compares +11%, extensions +7%. Frame code is 11% of Stogir samples vs 8% for LLVM: allocator wrappers (`sized-alloc`, `sized-resize`, `sized-reallocate`, `sized-free`, `raw-alloc`, `ScratchArena$allocate`, `bump`), `sx-items`, `code-node-parts`, `sccp-phi.input`, `Eq$slice<u8>$=`. `compiler.resolve` is the largest subsystem gap (AVec scans with string compares).

**Next, ranked:**
1. Buy ~3% generation (candidates: per-callee caching of `eligible?`'s callee scan and `closed-control?`, which rescan the callee at every site; SCCP's input duplicate for diffing; cheaper `pressure-class-into!` reservation queries), then re-apply `b7d5d00`.
2. Shrink-wrapping: prologue on edges leaving a frame-free entry region (`Eq$slice` length mismatch, `push!` fast path).
3. Allocator: split around cold calls so fast paths stay in caller-saved registers (`bump`), and keep cold paths from spilling PHI webs used by fast paths (`sx-items` stores its result to a frame slot twice).
4. Tail calls for register-pair (Option/Result) results: 3,428 call+epilogue sequences in tail position, ~1.1% of samples.
5. Spill/reload placement in high-pressure loops (`resolve-use` reloads values it does not use inside its inner loop).

## November 7 evening

Library `feature/branch-fusion` at `4b4eda0`; Coil `stogir/branch-fusion` at `1c8c3100` vendors it (quick FAST passes; Stogir-only bootstrap reproduces the seed object). Nothing installed or pushed.

**Status.** Full bootstrap (`bootstrap.py`, with LLVM rows) at `37f4a55`/`79cc79f1`: seed generation **Stogir 7.296 s vs LLVM 36.10 s = 4.95×** (goal 5×; need ≤ ~7.22 s). Runtime: matched hosts ~61.5B vs ~46B cycles (**~1.34×**); the bootstrap's native rows show 8.80 s vs 7.08 s generation work (1.24×). Goal ≤ 1.10×.

**Generation commits (all byte-identical except where noted):** disjoint register reservations from an advancing cursor (`9fe1d77`, −1.7%); pressure scans limited to the value's class mask (`cffc350`); fixed-use event sort by register buckets + merge sort (`1d2814a`); structure verified once in schedule preparation (`41311d9`); SCCP proofs carried into code generation, with owned/image SCCP compacting before final validation so 98% of functions reach the backend with a matching proof (`1824cb9`; compacted templates change inline-budget outcomes, matched hosts same cycles and identical outputs); four-lane content hash (`37f4a55`).

**Bug found and fixed (`4b4eda0`).** `bbd9683` emitted SEXT of a signed load as a 64-bit copy; after a W move of the I32 value (e.g. into a callee-saved register at a split), bits 32-63 were zero. Now the copy is used only in the value's original, unsplit allocation part. sext-load has a regression case. It surfaced through a CSE experiment that changed inlining in `graph.contains?`/`lookup`; found by hash-gated bisection over SCCP graphs and lldb.

**Measured and rejected this evening:** Euler-interval dominance in GCM placement (no gain); single-decode `uses.build` (no gain); multiply by (2^k+1)·2^m as shift-adds, fused into ADD/SUB (neutral to slightly worse on Apple cores: shifted adds are not cheaper than `mul`); global CSE of pure nodes (9% of pure nodes were duplicates, but +0.7B instructions and +0.5B cycles, likely longer live ranges and changed inlining, and +1.5% generation).

**Where the runtime gap is (unbiased `tsprof`, same source).** Functions present in both hosts take *fewer* samples under Stogir (0.89×); the gap is in functions LLVM inlined away (39K of 94K Stogir samples). Call overhead (prologue/epilogue/argument setup) is ~17% of the gap. Stack loads are the largest bucket (+24% of the gap). Of hot stack loads, the biggest class is reads of address-taken stack objects (5,972 samples), larger than spill reloads (3,636) or callee-saved restores (3,182). A clear instance: calls returning `Option`/`Result` in x0/x1 (call-results kind 1) store the pieces into a stack place and immediately reload them (`scratch.bump`). Direct kind-1 calls already project their pieces into registers (6,941 projected, 257 rejected), so the remaining struct traffic comes from elsewhere.

**Decision (user, November 7): the next project is struct promotion** — keep small struct values (Option/Result, dyn-call results, by-value params) in registers rather than stack memory. Step 1 is classifying the hot aggregate stack loads by source pattern (indirect/dyn call results, by-value parameter copies, local structs passed by address). Library `caafe51` (skip the post-promotion digest when promotion reports changes) is committed but not yet vendored.

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
