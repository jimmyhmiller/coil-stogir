# Inlining after induction-range optimization

The runtime target remains unmet. Adding `small-leaf=1` to the retained induction policy reduces IR-to-object generation time by about 13%, but a dedicated runtime repeat does not confirm a gain. Keep the original induction configuration as the runtime reference; retain this policy as a generation alternative.

All hosts compile the same fixed compiler source. `metadata.json` records source, generator and host identities; the paired generation metadata records exact commands and environment. The generator includes allocation snapshot diagnostics (library dd930d7, integration f4be62f1); those diagnostics do not change allocation. No LLVM generation comparison was repeated here.

## Policies

All Stogir hosts enable `COIL_STOGIR_LOOP_EVICT=1`, `COIL_STOGIR_LOOP_RELOAD=1`, `COIL_STOGIR_PREDICT=1`, and `COIL_STOGIR_INDUCTION=1`. `COIL_STOGIR_INLINE` is:

- induction: `small=80,small-scope=any,hoist=1`
- leaf80: `small=80,small-scope=any,small-leaf=1,hoist=1`
- leaf: `budget=1024,template=1024,small=128,small-scope=any,small-leaf=1,hoist=1`
- big: `budget=4096,template=2048,small=256,small-scope=any,hoist=1,always=1,pair=1,indirect=1`

Unspecified flags remain off. The leaf restriction applies to the small-function exemption, not every inline decision.

## Runtime

Three alternating rounds per comparison, serial measurements, identical output SHA-256 `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb` in all 33 runs. Hardware cycles, ratios against induction within that comparison:

| Comparison | Policy | Minimum ratio | Median ratio |
|---|---|---:|---:|
| 1 | leaf | 0.9932 | 1.0046 |
| 1 | big | 1.0165 | 1.0148 |
| 2 | leaf | 1.0011 | 0.9815 |
| 2 | leaf80 | 0.9805 | 0.9681 |
| 3 | leaf80 | 1.0019 | 1.0006 |

The larger policy regresses both statistics. Leaf-focused variants are mixed. The promising first leaf80 observation did not repeat. In comparison 3, induction takes 55.155B minimum / 55.946B median cycles versus LLVM's 43.141B / 43.700B (1.2785× / 1.2802×). This is not within 10%.

## Generation

Three alternating rounds, sum of backend generation timings (frontend excluded):

| Policy | Minimum seconds | Median seconds |
|---|---:|---:|
| induction | 9.737351 | 9.782569 |
| leaf80 | 8.443586 | 8.499338 |

Leaf80 reduces minimum generation by 13.29% and median by 13.12%. Each policy produces identical objects in all three runs, matching its runtime host object. This result alone does not establish the absolute 5× generation target.

## Reproduction and validation boundary

Use `../deferred-loop-splits/compare.py ROOT OUTPUT name=HOST ... --rounds 3` for runtime, and `../branch-facts/generation.py ROOT CANDIDATE OUTPUT --rounds 3 --policies induction leaf80` for generation. Runtime JSON, compressed raw stderr, generation JSON, hashes, and commands are retained alongside this report. The measured generator and toolchain are preserved in integration `build/region-recolor/measured-candidate*`.

These experiments use existing inlining policy switches; no inliner implementation changed. All fixed-workload outputs match. Broad library/native validation belongs to the preceding induction/load-hoisting checkpoint; it has not been rerun for leaf80 here. No policy was installed or promoted as a runtime improvement.
