# Overflow-safe unit-step induction ranges

Runtime-first research, implementation `3752b9b` on `research/induction-ranges`, based on the experimental
branch-fact pass (`a664c48`). The new option is `COIL_STOGIR_INDUCTION=1`; it
includes dominating branch facts and remains disabled by default.

## Proof and scope

A candidate PHI must have one external incoming edge and one natural back edge,
identified from the original CFG's dominance relation. The CFG edge positions
select the corresponding PHI inputs. Both MERGE and LOOP_BEGIN are supported;
input order is immaterial. The initial value is a literal and the recurrence is
an integer ADD by one, optionally through equal-width integer bitcasts.

The proof uses strict **signed** comparisons that dominate the back-edge block
within the iteration. Signedness comes from the comparison opcode, even when
the scalar storage type is u64. Endpoints use i128 arithmetic so 64-bit boundary
reasoning does not overflow.

- A back-edge guard `phi < other` guarantees the increment cannot overflow on
  that edge. The PHI lies in `[initial, signed MAX]`. No global range is assigned
  to the ADD: on an exit path it could still wrap.
- A back-edge guard `next < other`, with `initial < signed MAX`, proves the PHI
  lies in `[initial, signed MAX-1]`; the ADD lies in `[initial+1, signed MAX]`.
  This covers the actual hot counter initialized to -1 and incremented before
  its body check.

These are inductive proofs over the immutable input, not facts inferred from
one partially optimized iteration. No inferred range justifies another
recurrence. Non-unit steps, additional incoming edges, unsigned guards and
non-strict bounds are conservatively excluded. An unsigned comparison of a
signed interval crossing zero uses the full unsigned interval; endpoints cannot
be reinterpreted as if their ordering were unchanged.

Only proven IF condition edges change. Shared comparisons stay intact. SCCP
performs control, PHI and root repair. Existing validation remains enabled.

## Focused validation

`tests/induction-ranges.coil` passes with Stogir O3 and debug checks:

- All 256 8-bit initial values, both loop forms and three guard kinds, each
  simulated against all 256 bounds. Every reached query checks the proof.
- Independent interval-comparison checks cover all ten integer comparisons,
  singleton intervals, equality/inequality, and unsigned sign-crossing ranges.
- Native executions cover 8-, 32- and 64-bit limits, both signed and unsigned
  storage, MERGE/LOOP_BEGIN, reversed PHI slots, and continuing IF_FALSE.
- Unsafe cases include wrapping/non-strict/unsigned guards, unguarded loops,
  non-unit steps, and an extra unbounded back edge.

The preceding `tests/branch-facts.coil` still passes. Whole-library validation
has 297/299 standalone programs passing; only the two previously recorded
failures remain (`jit-parameter-specialize`, `private-leaf`). All 73 linked AOT
consumers pass, with 5,410 freshly generated fixture objects copied into a
private directory before linking. Quick FAST passes with induction enabled
(71.3s under concurrent validation/trace load, not a performance measurement).
The source and vendored library trees match byte for byte. Full FAST, live
emission and current-source full bootstrap remain final-delivery gates.

## First matched runtime round

Same fixed Coil source and hosts as the branch-fact experiment. Runtime policy:
`small=80,small-scope=any,hoist=1`, loop eviction/reloads and prediction enabled.
Three alternating-order rounds; all twelve outputs match the fixed seed SHA256
`9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.

| Host | Minimum cycles (billions) | Median cycles (billions) |
|---|---:|---:|
| LLVM O3 | 43.035 | 43.504 |
| Allocation regions | 55.633 | 55.647 |
| Branch facts | 55.313 | 56.427 |
| Branch facts + induction | 54.662 | 54.807 |

Induction is 1.74% lower minimum / 1.51% lower median than regions, and
1.18% / 2.87% lower than branch facts alone. Runtime remains 1.270 / 1.260x LLVM,
outside the 1.10 target. The third induction run was 59.317B cycles, so the
signal needs another matched round. Raw results are in `round1/`.

The host object is
`221639412cd1c1c5dd75b714943a35c3043deeed7c27fbdae1fbc55582b9f09b`.
`primitive.diff` compares the actual all-functions branch-fact host to this
host: `primitive-providers-in` loses its negative-index `cmp; b.lt` and the
unreachable failure path, eight static instruction lines. Target addresses
are normalized in the diff. Binaries and original disassembly are under
`build/induction-ranges/` (Coil and library worktrees).

A single host-generation observation was 9.737s; that is not a paired cost
measurement. The eventual goals remain at least 5x LLVM generation and runtime
within 10%. Runtime-first research authorizes temporary generation costs,
not a weaker completion criterion.

## Repeated runtime measurement

A second twelve-run alternating round also produced the same seed object in
every run (`round2/`):

| Host | Minimum cycles (billions) | Median cycles (billions) |
|---|---:|---:|
| LLVM O3 | 43.207 | 44.255 |
| Allocation regions | 55.057 | 56.084 |
| Branch facts | 55.167 | 55.867 |
| Branch facts + induction | 54.286 | 55.008 |

The combined policy is 1.40% lower minimum / 1.92% lower median than regions,
and 1.60% / 1.54% lower than branch facts alone. Both rounds have lower minimum
and median cycles. The remaining ratio to LLVM is 1.256 / 1.243, still outside
1.10. Carry the induction option forward as a modest research improvement;
do not treat it as meeting the overall goal.

## Next loop opportunity

`lookup.trace.gz` captures `coil.compiler.ast.src-mod-lookup-at` from this
candidate and reproduces the exact host object. Its header LOAD131 reads the
ArrayList length through invariant address130; the loop (blocks6–16) contains
no stores or calls. The unique entry follows CALL60, so a header-load hoisting
proof can preserve its order after that call and its original first execution,
including zero-trip loops. Body LOAD133 reads the data pointer only after the
guard; moving that load unconditionally would add a potentially faulting read.
Guarded hoisting after rotation is a separate proof obligation. No load-hoisting
implementation is included here.

## Incremental generation cost

Three alternating rounds using the same candidate (`../branch-facts/generation.py`
with `--policies facts induction`). Frontend time is excluded. All objects
within each policy match its measured runtime host byte for byte.

| Policy | Minimum seconds | Median seconds |
|---|---:|---:|
| Branch facts | 9.281 | 9.302 |
| Branch facts + induction | 9.547 | 9.573 |

The induction proof adds 2.86% minimum / 2.91% median generation time. This is
an incremental measurement, not a fresh absolute LLVM speedup claim. The
previous branch-fact absolute result was already below 5x, and the runtime
ratio remains outside 1.10x. The research improvement does not complete either
goal. Raw timing streams, full hashes and source-tree metadata are saved in
`generation/`. The measured candidate is preserved in the integration worktree
at `build/induction-ranges/measured-candidate` with its toolchain record.

Library implementation `3752b9b`; integration `e885ff63`. No install or push.
Root user-owned handoff and results remain untouched.
