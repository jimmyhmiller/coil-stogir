# Dominating integer branch facts

Runtime-first research, implementation `3edd0e0` on `research/branch-facts`, based on the retained
allocation-region implementation (`c6f7ef3`). The experiment is off by default;
Coil enables it with `COIL_STOGIR_BRANCH_FACTS=1`.

The pass uses the original graph's dominators to prove individual IF outcomes
from ancestor IF_TRUE/IF_FALSE projections. Relations use the three possible
integer orderings (less, equal, greater). Operand identity may cross equal-width
integer bitcasts, but not loads, extensions, truncations, or floating conversions.
Signed and unsigned facts have independent masks, even for equality queries:
signed `x <= y` and unsigned `x >= y` do not imply `x == y`.

Only the condition edge of each proven IF changes. A shared comparison keeps
its original meaning elsewhere. All proofs precede edits; a second SCCP run
repairs control, PHIs and root lists. Existing structural verification and
allocation verification remain enabled. This first version deliberately pays
for an additional full preparation and, for changed graphs, SCCP.

The adapter applies the option to ordinary module callers, private leaf
precompilation, and modules with no certified private callees. Private leaf
precompilation uses an inactive context so it cannot read an unsealed registry.

## Workload and initial measurement

Fixed Coil source: `coil/.worktrees/stogir-branch-fusion`, `d1efe960`.
All runtime hosts compile that source with Stogir O3. Their own generation uses:

```
COIL_STOGIR_INLINE=small=80,small-scope=any,hoist=1
COIL_STOGIR_LOOP_EVICT=1
COIL_STOGIR_LOOP_RELOAD=1
COIL_STOGIR_PREDICT=1
```

The first candidate enabled branch facts for module callers only. Three
alternating-order rounds, with every emitted seed object SHA256 equal to
`9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`:

| Host | Minimum cycles (billions) | Median cycles (billions) |
|---|---:|---:|
| LLVM O3 | 42.781 | 44.375 |
| Allocation regions | 57.062 | 57.211 |
| Regions + caller branch facts | 55.430 | 56.089 |

Improvement versus this round's region baseline: 2.86% minimum, 1.96% median.
Runtime ratio to LLVM remains 1.296 / 1.264, outside the 1.10 target. Retired
instructions fall by roughly 1.2 billion. `primitive.diff` confirms a redundant
bounds compare/branch removed from `primitive-providers-in`, together with
allocation/layout changes. It normalizes branch target addresses for readability;
the actual binaries and disassembly are in `build/branch-facts/`.

The first host object is
`a91375d2587101e6c7c445cd1f371fe3f2a9c21e41816369107d26e15c23d272`.
The final adapter's host, including private leaves, is
`8a106bb82c31e629099595ee2646047f89f71689b460cba65c4583a7cc1a193b`.
Its completed matched measurement is below; do not assign the first host's timings to it.

## Completed adapter measurement

Three further alternating rounds with private leaf coverage, all nine objects
again seed-identical (`final-runtime/results.json`):

| Host | Minimum cycles (billions) | Median cycles (billions) |
|---|---:|---:|
| LLVM O3 | 42.819 | 43.129 |
| Allocation regions | 54.807 | 56.277 |
| Regions + all branch facts | 54.471 | 56.955 |

The signal is mixed: 0.61% lower minimum cycles, 1.20% higher median cycles.
Minimum/median runtime ratios to LLVM are 1.272 / 1.321. Retired instructions
fall by about 1.7B, but that does not establish a cycle improvement. Keep this
as an opt-in research pass, not a default policy or a claimed reliable win.
The earlier caller-only candidate had a stronger cycle result; these rounds
do not isolate leaf coverage from run-to-run variation.

## Validation

`tests/branch-facts.coil` checks all 400 one-source predicate/projection/operand
order combinations, 800 two-source combinations for equality/inequality, and
representative native JIT executions over signed-boundary inputs. It also checks
shared comparison consumers, control-flow joins, and a new load after a store.
All pass with debug checks. Quick FAST with the experimental option enabled
passes (90.5 seconds under simultaneous six-way library validation load; this is
not a performance measurement). Whole-library validation: 296/298 standalone programs pass. The two failures
are the previously reproduced `jit-parameter-specialize` (expected expansion)
and `private-leaf` (wrong signature accepted). All 73 linked AOT consumers pass
using 5,410 unique freshly generated object fixtures copied to a private directory.
The generic suite's unlinked consumer failures are not counted as standalone
failures; `linked.json` records their proper linked runs. Full FAST, live emission
and current-source full bootstrap remain delivery gates for the overall goal.

Runtime comparisons use `../deferred-loop-splits/compare.py`, which rejects
failed compilations and unequal output objects. `generation.py` alternates LLVM,
region policy, and region-plus-facts using one candidate, saves raw timings,
checks deterministic objects within each policy, and excludes frontend time.

## Next proof needed

The saved `primitive-providers-in` graph has a counter PHI initialized to -1,
an ADD by one, a signed loop bound on the updated value, and a redundant
negative-index check on the body path. These loops use MERGE nodes; recognizing
only LOOP_BEGIN misses them. A range proof must identify natural back edges by
dominance, map them to PHI slots, and prove the recurrence cannot overflow.
A positive increment alone is insufficient. Details are in the project pad's
`branch-facts-next-range-proof` cell. No induction-range optimization is included
in this commit.

## Paired generation

One frozen candidate, three alternating rounds, frontend excluded:

| Policy | Minimum seconds | Median seconds |
|---|---:|---:|
| LLVM O3 | 35.652 | 39.944 |
| Region baseline with the runtime policy above | 8.955 | 9.036 |
| Same policy plus branch facts | 9.453 | 9.593 |

The extra pass costs 5.56% minimum / 6.17% median generation time. Its speedup
versus LLVM is 3.772x minimum / 4.164x median, short of 5x. This is the aggressive
runtime-oriented inline policy, not the older default-policy generation result.
The runtime-first research authorization allows the temporary cost; it does not
change either eventual acceptance target.

All three objects within every policy are identical. The LLVM object matches
the retained LLVM runtime host's original object (`ffe3482e...77f44`); the
region object matches its measured host (`8449a7d2...ca4b7`); the facts object
matches the completed adapter host (`8a106bb8...193b`). The LLVM timings vary
substantially across the three samples (46.920, 35.652, 39.944 seconds), so both
minimum and median are reported. Raw timing streams are saved compressed in
`generation/`, along with full hashes, commands and candidate metadata.

Implementation and integration commits: library `3edd0e0`, Coil `2bca489f`.
The research branches remain separate from installed tools; nothing is pushed
or installed. The original root handoff and result directory are untouched.
