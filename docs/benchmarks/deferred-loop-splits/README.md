# Deferred nested-loop register splits

November 8, 2026. Research only: runtime within 10% of LLVM now takes priority
over generation speed. Generation cost remains measured; recovering the 5×
target is a later phase. No compiler is installed or pushed by this experiment.

The hypothesis is that moving a call-conflicted interval into a new register
at a nested loop's entry can spill outer values even when the body never runs.
The experiment defers reassignment to the body when its first register use is
there. v1 covers values born in an enclosing loop; v2 also covers header-born
values. Fixed register uses bound legal splits. Header uses retain the original
policy, and all splits remain block boundaries resolved by the normal CFG edge
transfer machinery. This is a structural rule with no function-name exceptions.

Both library and integration worktrees are on `research/deferred-loop-splits`.
The fixed workload remains Coil `stogir-branch-fusion` at d1efe960. LLVM host:
`build/n8-full8/host-llvm/bin/coil` in that worktree. The prior host is
`stogir-inline-policy/build/hp17/predict2/bin/coil`.

All general-option runs use:

```
COIL_STOGIR_INLINE=small=80,small-scope=any,hoist=1
COIL_STOGIR_LOOP_EVICT=1
COIL_STOGIR_LOOP_RELOAD=1
COIL_STOGIR_PREDICT=1
```

The no-eviction comparison drops only `COIL_STOGIR_LOOP_EVICT` from both hosts.
Build and diagnostic artifacts are in the integration worktree's
`build/deferred-loop-splits/`. `compare.py` reverses host order on alternate
rounds, rejects nonzero exits and compares the SHA-256 of every emitted object.
All measurements are local macOS AArch64 hardware cycles.

| Round | LLVM minimum / median B cycles | Prior minimum / median | New minimum / median |
|---|---|---|---|
| v1, loop eviction enabled | 43.357 / 43.769 | 57.118 / 59.103 | 56.591 / 56.961 |
| v2, loop eviction enabled | 45.231 / 45.492 | 57.934 / 58.835 | 56.747 / 58.752 |

These are noisy three-round comparisons, not accepted performance wins. In v2,
minimum improves 2.05% but median only 0.14%. Neither changes the instructions
of `primitive-providers-in` (ignoring symbol addresses). The proactive
`cold-owner` eviction runs before free-register assignment and can override
this policy. Disabling it does change the function's allocation, but outer-loop
reloads remain. Results of that comparison will be recorded below.

One-off generation observations: v1 8.600s; v2 8.338s; no-eviction old/new
9.231/8.384s. These were not alternating isolated measurements and cannot
establish a compile-time speedup.

Validation: the new split regression fails on the preceding library and passes
with the experiment. Existing loop-entry/reload/eviction/call-hole tests pass.
Pressure oracle, AArch64 allocation, private call allocation, JIT pressure,
JIT switch pressure and module execution passed for v1; v2 repeats allocation,
native pressure and module checks. All completed host runs reproduce the seed
object `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.
Full library suite and FAST have not been run; this is not release validation.

## Final no-eviction comparison and disposition

| Host | Minimum B cycles | Median B cycles |
|---|---:|---:|
| LLVM O3 | 44.987 | 46.663 |
| Prior allocator, no loop eviction | 57.296 | 59.024 |
| Experimental allocator, no loop eviction | 56.662 | 58.116 |

The experiment improves minimum 1.11% and median 1.54% in this round; the
instruction count is effectively unchanged (~214B). Run-to-run spread is
larger than the difference. Best experimental minimum remains 1.260× LLVM,
not the required ≤1.10×. All 27 workload executions across the three rounds
produced the same seed object. These results do not establish a reliable win.

The experimental source and test are preserved in `experiment.patch`; live
library and integration sources and the original candidate have been restored.
The original user-owned untracked tools and root checkout were untouched.
The patch applies to library parent 015b4a1. It is not a delivered optimization.
`ab1` used the existing shell comparison with fixed host order. `ab2` and `ab3`
used `compare.py` with order reversal and fail-fast hash checks. Raw outputs
are stored beside this report.

Next research should model allocation cost across CFG regions and retain an
outer value in its register on the bypass edge while splitting ownership only
on the path through the inner body. Use frequency-weighted use costs and
region-local conflict splitting together; next-use distance plus a loop-entry
heuristic does not express that choice. The existing exact block-count tools
can validate whether the zero-trip path actually loses its spill reloads.
More inlining should wait for that result. Full release checks are deferred
because no compiler-source change is retained.
