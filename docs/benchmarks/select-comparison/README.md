# Direct comparison flags for conditional selects

The target remains unmet. This extension removes redundant Boolean materialization and has a favorable first comparison, but the dedicated repeat is mixed. Keep the induction runtime baseline and leave `COIL_STOGIR_IF_CONVERT` disabled by default.

## Implementation and boundaries

Library 0e1f96c; integration 404718c5. With the existing if-conversion research option enabled, persistent matching can fuse a single-use, unobserved, same-block 64-bit integer comparison into a 32/64-bit integer COND. Ordered MIN/MAX choices retain their existing rules. Rooted/shared predicates, narrow comparisons, RLOAD/overflow conditions and noninteger results retain ordinary lowering.

Before liveness, the matching plan replaces the Boolean use with the comparison inputs and both choice inputs. The Boolean definition is omitted. Allocation constraints require the actual inputs at the select and its result afterward. The emitter consumes the stored comparison recipe, captures NZCV, materializes choices without changing flags, and emits CSEL or the appropriate CSET polarity. There is no post-allocation operand discovery or graph mutation. Existing matching APIs and default behavior remain unchanged.

The hot `primitive-providers-in` function now has two direct CMP/CSEL sequences and four fewer static instructions than conversion alone. Disassembly is included. This is a static observation, not a runtime estimate.

## Runtime: alternating fixed-source hosts

Each comparison has three alternating rounds, without concurrent builds/tests. All 21 workload outputs match `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`. Exact host/source identities and raw stderr are retained.

| Comparison | Host | Minimum cycles (B) | Median cycles (B) |
|---|---|---:|---:|
| 1 | LLVM | 43.832 | 44.069 |
| 1 | induction | 55.971 | 56.357 |
| 1 | conversion alone | 56.384 | 56.527 |
| 1 | conversion + fusion | 55.188 | 55.303 |
| 2 | LLVM | 45.243 | 45.924 |
| 2 | induction | 54.963 | 55.802 |
| 2 | conversion + fusion | 55.411 | 55.414 |

Fusion versus induction: comparison 1 improves minimum/median by approximately 1.4%/1.9%; comparison 2 regresses minimum 0.8% while improving median 0.7%. Medians are favorable in both comparisons, but the minimum result does not repeat. LLVM also slows materially in the second comparison, so its better relative ratios are not evidence of a new compiler improvement. No runs are discarded. This evidence is insufficient to replace the retained baseline.

Fusion removes roughly 3.5B executed instructions from conversion alone, but still executes more instructions than induction (about 209–210B versus 206.5B). The runtime target remains well outside 10% in both comparisons.

## Generation

The generation helper calls the current combined configuration `selects` (the same environment option as conversion alone, but a different preserved generator). Three alternating rounds produce identical objects matching their hosts:

| Policy | Minimum seconds | Median seconds |
|---|---:|---:|
| induction | 9.389 | 9.422 |
| conversion + fusion | 10.096 | 10.189 |

IR-to-machine generation increases about 7.5% minimum / 8.1% median, excluding frontend time. LLVM generation was not remeasured. The baseline object is unchanged (`22163941…`); combined object is `40fb5839…`.

## Validation and reproduction

- 300/302 standalone tests pass. The two known failures remain unchanged: `jit-parameter-specialize` (expected expansion) and `private-leaf` (wrong signature accepted).
- All 73 existing linked AOT consumers pass using 5,410 fresh fixtures.
- New comparison matrix: 87,480 native answers covering all ten integer predicates, positive/negative immediate and register comparisons, result widths, literal choices, shared/rooted/narrow rejection. A 40-live-load pressure case exercises spilling and use lifetimes.
- Existing ordered-choice matrix passes 1,219,680 native answers; conditional selection and general conversion tests pass.
- C-linked Mach-O tests pass for single-result fusion and shared multi-result conversion.
- Compiler FAST quick passes with the combined policy (94.4s under concurrent validation load).

The vendor tree matched the library at the measured build. Preserved generator/toolchain: integration `build/select-comparison/measured-candidate*`. Host: `build/select-comparison/host/bin/coil`. Use `../deferred-loop-splits/compare.py` for runtime and `../branch-facts/generation.py --policies induction selects` for generation. No installation, push or default promotion.
