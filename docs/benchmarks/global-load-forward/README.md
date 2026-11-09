# Global redundant-load elimination

The combined performance target remains unmet. This pass is a validated, opt-in research component; the two runtime comparisons do not establish a repeatable gain. The retained induction runtime policy is unchanged and `COIL_STOGIR_GLOBAL_LOADS` stays off.

## Implementation

Library `55ade43`; compiler integration `156480d3`. The vendor trees match byte for byte. The compiler threads the option through module, private-leaf and fallback emission, before branch facts and induction ranges. Defaults are unchanged.

The independent pass selects an earlier, exact typed scalar LOAD using scheduled position and dominance. A separate backward traversal checks every intervening control path, including all merge inputs and loop back edges. A store must be byte-range disjoint; a call must satisfy the existing address-preservation proof. Unknown effects, volatile/atomic operations, register/lifetime effects and unsupported controls reject reuse. No read is inserted or speculated.

Each batch analyzes an immutable graph. Shared local/global forwarding machinery remaps data and control independently, retains stable value identities and preserves control observations for rooted loads. Fresh verified schedule/dominance facts are rebuilt after every batch. The number of ordinary loads must strictly decrease; pointer forwarding can expose another removable load in the next batch. No workload names, measured counts or profile exceptions drive the transformation.

## Runtime

Both comparisons alternate LLVM, induction and global-forwarding hosts for three rounds, reversing order every other round. No build or test ran concurrently. All 18 outputs match the fixed workload seed SHA256 `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`. Host/source identities are in `metadata.json`; individual results and raw timing stderr are retained.

| Comparison | Host | Minimum cycles (B) | Median cycles (B) |
|---|---|---:|---:|
| 1 | LLVM | 42.864 | 42.901 |
| 1 | induction | 54.692 | 54.776 |
| 1 | global forwarding | 54.023 | 54.639 |
| 2 | LLVM | 42.639 | 42.993 |
| 2 | induction | 54.211 | 54.760 |
| 2 | global forwarding | 54.637 | 54.793 |

Against induction, the first comparison improves minimum/median cycles by 1.225%/0.250%. The repeat regresses them by 0.786%/0.060%. The median runtime remains about 1.274× LLVM, outside the 1.10× target. No samples are discarded. Median retired instructions decrease by approximately 0.30B and 0.33B, only 0.14–0.16% of the workload total.

Static disassembly counts change in 1,279 matching functions, with 3,340 fewer instructions and 3,105 fewer load instructions overall; neither host has unmatched symbols. These counts include spill loads and subsequent optimization effects, not just eliminated graph loads. They are not dynamic counts or cycle predictions. `primitive-providers-in` and `src-mod-lookup-at` retain their prior instruction counts. The latter's repeated field reads occur at one static site per loop, requiring loop hoisting rather than a dominating prior load. The earlier hoisting experiment already improved that local code without demonstrating a whole-workload win.

## Generation

Three alternating rounds use the same preserved candidate and fixed source, with per-function `COIL_CODEGEN_TIMINGS` summed over IR-to-machine generation, excluding frontend work.

| Policy | Minimum seconds | Median seconds |
|---|---:|---:|
| induction | 9.339359 | 9.401812 |
| global forwarding | 10.216701 | 10.238031 |

The pass increases generation by 9.39% minimum / 8.89% median. LLVM generation was not remeasured, so this is a relative cost, not a fresh absolute 5× comparison. Every policy emits identical bytes in all rounds, matching its measured host. Induction remains `221639412cd1c1c5dd75b714943a35c3043deeed7c27fbdae1fbc55582b9f09b`; global forwarding is `7ed2d2a91dda9695b08c706a28349c1f30138fbec902f818c2d6594d060e9919`.

## Validation

- 301/303 standalone library tests pass. The two existing failures are unchanged: `jit-parameter-specialize` (expected expansion) and `private-leaf` (wrong signature accepted).
- All 73 linked AOT consumers pass with 5,410 freshly generated object fixtures. The generic standalone runner's link-consumer results are superseded by this proper linked run.
- Focused tests exercise dominating/non-dominating loads, diamonds, equal/different addresses and types, aliasing pointer arguments, partial-overlap and disjoint stores, readonly/unknown calls, volatile/atomic barriers, rooted values and retained effects.
- Loop cases include zero-trip null pointers, writing/disjoint back edges, multiple back edges, guarded body loads, and retaining a header load without a pre-entry source. Original, explicitly transformed and optional O3 native execution agree; all memory effects are checked.
- Pointer-chain coverage requires a second immutable batch, then verifies the fixed point and source immutability.
- C-linked Mach-O checks pass for invariant, guarded and writing loops. Existing local forwarding/mem2ssa regression coverage passes after extracting the common remapper.
- Compiler quick FAST passes with global forwarding enabled (63.3 seconds under concurrent validation load, not a timing result).

Full FAST, live emission and current-source release bootstrap remain acceptance gates for the overall goal. This research result does not meet that goal. Nothing is installed or pushed.

## Reproduction and retained artifacts

Preserved generator/toolchain: integration `build/global-load-forward/measured-candidate*`; host: `build/global-load-forward/host/bin/coil`. Runtime helper: `../deferred-loop-splits/compare.py`. Generation helper: `../branch-facts/generation.py --policies induction global-loads --rounds 3`. Both use the fixed Coil `stogir-branch-fusion` source. Static counts can be regenerated with `static-counts.py BEFORE_HOST AFTER_HOST --objdump /opt/homebrew/opt/llvm/bin/llvm-objdump`.

The generation policy adds `COIL_STOGIR_GLOBAL_LOADS=1` to the retained settings: inline `small=80,small-scope=any,hoist=1`, loop eviction/reload, prediction and induction enabled. Other research options remain off.
