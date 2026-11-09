# General integer diamond conversion: first measurement

The pass is correct on the validation below, but this first measurement shows no reliable runtime improvement. Minimum cycles regress 0.19%, median improves 0.21%. Keep `COIL_STOGIR_IF_CONVERT` off by default. The runtime target remains unmet.

## Implementation

Library abe632b; integration 17dc3d7c. A late optional pass converts closed two-arm diamonds with up to four integer PHIs into COND nodes. Incoming values must dominate the branch in the prepared schedule, or be a DAG of total integer expressions costing at most four units across the whole diamond (multiply costs three). Speculation excludes memory, calls, division/remainder, overflow operations, floating-point work and vectors. RLOAD/OVERFLOW values are rejected. Typed operands and CFG structure are verified before planning.

All recipes in a batch are proved against one immutable graph; closed structural regions do not overlap, and branch/merge/value references survive. The existing END/BEGIN convention preserves positive control identities, removed roots map to the retained branch, and preparation is rebuilt after each batch. The pass terminates because each conversion removes one IF and introduces none. Graph ownership is acquired only when a change occurs; the source is unchanged.

This version uses the existing general COND emitter. Inspection exposes a remaining `CMP; CSET; ...; CMP; CSEL` sequence. A separately measured follow-up should redirect comparison inputs before liveness and consume their flags directly; that follow-up is not included in these numbers.

## Matched fixed workload

All hosts compile the same source under the same runtime settings. See JSON metadata and commands. Three alternating rounds, no concurrent builds/tests. All nine emitted objects match seed SHA-256 `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.

| Host | Minimum cycles (B) | Median cycles (B) |
|---|---:|---:|
| LLVM | 42.850 | 43.164 |
| induction | 55.355 | 55.883 |
| conversion | 55.461 | 55.766 |

Conversion executes about 212.5–212.7B instructions versus induction's 206.5–206.6B. The inspected `primitive-providers-in` function has two CSEL instructions and three fewer conditional branches, but this static observation is not a cycle prediction. Its full disassembly is included.

Three alternating generation rounds (frontend excluded) produce identical per-policy objects in every round. See `summary.json` for exact timings: conversion costs roughly 8–9% more generation time. The baseline generation object matches the retained induction host (`22163941…`); conversion matches its host (`f73f6459…`). LLVM generation was not remeasured.

## Validation

- 299/301 standalone library tests pass. The same two recorded failures remain: `jit-parameter-specialize` (expected expansion), `private-leaf` (wrong signature accepted).
- All 73 existing linked AOT consumers pass, using 5,410 fresh fixtures.
- New focused structural/native tests cover reversed branches, shared multi-PHI expressions, adjacent diamonds, fixed point, source immutability, observed roots, work limits, rejected division/loads/floating conversion, and integer boundary values. A null pointer on an untaken load path remains safe with conversion enabled.
- The new C consumer links the generated Mach-O object and passes its boundary matrix.
- Compiler FAST quick passes with the full induction-plus-conversion policy (68s under concurrent validation load).

Source and vendor trees were identical when building the measured generator. The preserved generator/toolchain are under integration `build/general-if-conversion/measured-candidate*`. The existing helper `../branch-facts/generation.py` supports policy `selects`; runtime uses `../deferred-loop-splits/compare.py`. No install, push or default policy change.
