# Native regional allocation: first full-workload measurement

The native regional pass is implemented and measured. It removes the actual
empty-inner-loop reloads in `primitive-providers-in`, but the full workload
improves only 0.45% over the retained induction host. Runtime remains 1.2677×
LLVM. Generation is much slower. The joint ≥5× generation / ≤1.10× runtime goal
is not met; the option stays disabled by default.

## Implementation and exact native evidence

Library `579c817` adds `allocation-regional`, scoped recoloring, and native
pipeline integration. Coil `d4b459cc` vendors the library unchanged and exposes
`COIL_STOGIR_REGIONAL=1` in all three adapter paths. It is separate from
`COIL_STOGIR_RECOLOR`; this experiment uses regional allocation with rotation,
without whole-child recoloring. The static flow component was added in
`bb62ffd`; the independent regional research is in `../zero-trip/`.

Regions come from the CFG and loop depth, smallest first. Each candidate owns
a deep partition of exact live ranges and uses. Outside assignments are frozen;
only strictly improving, machine-phase-legal bounded search transactions commit.
A no-change candidate is discarded without changing the original parts/index.
Typed spill homes and final callee-save areas use the normal allocation path.
Balanced static flow weights reuse the predictor; no function filters, captured
register assignments or measured profile probabilities enter compiler policy.

The automatic native result matches the independent research assignment at all
20,850 live-value positions, with no differences. Complete transfer costs also
match (54,072,862 → 34,290,177). The full compiler host confirms the same hot-path
code shape as the replay:

- Relative PC 0x170 branches to 0xc4 for an empty inner loop.
- Two register moves lead directly to 0x480, after body-exit reloads at 0x468,
  0x46c and 0x470.
- Outer-value stores occur only on body entry at 0x174, 0x17c and 0x184.
- Some eager stores of inner temporaries still precede the guard, including a
  duplicated store at 0x158/0x15c. The path is not free of all stack traffic.

The native object's bytes differ from the assignment-injection fixture because
partition grouping lets normal home-establishment analysis place stores later.
This is not an assignment discrepancy. The new `primitive-host.dis.gz` verifies
these offsets in the actual measured host at symbol base 0x44a298.

## Runtime

Three serial alternating rounds; all twelve outputs match the fixed seed
`9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.
Source and generator identities are in `metadata.json`; rows and compressed raw
hardware-counter output are in `runtime/`.

| Host | Minimum cycles (B) | Median cycles (B) | Median / LLVM |
|---|---:|---:|---:|
| LLVM | 42.365 | 42.456 | 1.0000 |
| Retained induction | 54.036 | 54.061 | 1.2733 |
| Induction + rotation | 54.462 | 54.525 | 1.2843 |
| Induction + rotation + regional | 53.766 | 53.820 | 1.2677 |

Regional allocation reduces median cycles by 1.293% against rotation alone and
0.446% against induction. The medians still need a further 7.119B cycle reduction
to reach 1.10× LLVM. Instructions are 206.187B versus induction's 205.963B and
rotation's 209.072B; a lower transfer proxy does not imply a comparable total
runtime gain. All task-owned build/test jobs had completed before timing.
Background macOS analysis processes remained active; comparisons alternate
within the same period rather than mixing historical timings.

## Generation

A separate **single** serial comparison uses the same preserved generator and
source. These are sums of IR-to-machine backend timings, excluding frontend.
Do not treat one observation as repeated acceptance evidence.

| Policy | Seconds |
|---|---:|
| Retained induction | 9.283006 |
| Regional + rotation | 227.601914 |
| LLVM O3 | 34.807803 |

Regional generation costs 24.518× induction. LLVM/regional is 0.15293×, far below
the required 5× speedup. The regional object exactly reproduces the runtime
host object `edef6c97…`; induction reproduces the retained object `22163941…`.
The initial host build occurred during validation and is not the generation
measurement above. The new fresh LLVM observation also must not be replaced
with a more favorable historical generation baseline.

## Validation and remaining gates

- New partition tests check independent ownership, holes, all uses, fixed
  reservations and frozen scope. Existing whole-child recoloring tests pass.
- The nested-loop fixture changes emitted bytes with regional allocation. It
  checks every result for zero/nonzero outer and inner trips, calls, register
  pressure and wrapping inputs in both JIT and C-linked AOT execution.
- The full run passed 306/308 standalone library programs. Follow-up test
  commit `e34da76` corrects the two stale test assumptions, and both focused
  native reruns pass without production changes. Together these cover all 308
  programs; this is not a newly repeated full suite. See the
  [test-contract evidence](../../../validation/regional-test-contracts/README.md).
- All 73 linked consumers pass using 5,410 freshly generated, privately copied
  and hashed object fixtures. Standalone runs of linked consumers without link
  flags are superseded by this linked run.
- Quick FAST passes with regional/rotation settings (54.8s under concurrent
  validation load, not a performance measurement).
- Full FAST, live emission, and a final repeated same-source bootstrap remain
  acceptance gates once a configuration meets the performance targets.

The source/vendor trees match. Candidate SHA-256 is
`f5d103eee3e877b4d108aa7b879e6f199fe0d3098f9284e035b75d5957cce754`, preserved
at integration `build/regional-native/measured-candidate*`. Nothing installed
or pushed.

## Reproduction and next interaction experiment

The fixed source is Coil `.worktrees/stogir-branch-fusion`; measured hosts are
under integration `.worktrees/stogir-inline-policy/build/regional-native/`.
Retained settings are `small=80,small-scope=any,hoist=1`, loop eviction/reloads,
prediction and induction. The regional host adds rotation and regional allocation.
Use `docs/benchmarks/deferred-loop-splits/compare.py` with the
LLVM, retained induction, `rotate-control/bin/coil`, and `host/bin/coil` hosts.
Generation uses `docs/benchmarks/branch-facts/generation.py --rounds 1 --policies
induction regional llvm`; its archived metadata includes full commands/settings.

The next experiment tests broader inlining with the now-implemented regional
pass. Build both rotation-only and regional hosts using
`budget=4096,template=2048,small=256,small-scope=any,hoist=1,always=1,pair=1,indirect=1`.
That policy previously regressed before regional splitting existed. The pending
interaction experiment is not a new runtime result or a promoted policy.
