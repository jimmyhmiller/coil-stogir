# Equal-count right/left shift masking

This experiment starts from retained library source at `3a4b9c0`; it does not include the mixed contained-view-before-PHI ordering experiment. A captured primitive-provider graph has a 64-bit SHL consuming SAR, both by five. The generated host previously emitted two shifts.

The AArch64 matcher selects the existing AND-immediate tile for SHL(SHR/SAR) with equal nonzero masked constant counts and equal 32/64-bit integer types. The left shift discards any sign-fill from SAR. Zero counts, unequal counts, dynamic counts, narrow/address types and width changes retain ordinary lowering. Producer and consumer must be in the same scheduled block. Graph identities stay unchanged; selected machine-use edges replace the original edge before liveness, and rooted/shared producers remain live.

A later indexed-address match may absorb the already-selected outer shift. Cascading retirement now subtracts its selected unary input rather than its original graph edge, keeping machine reference counts accurate. This is necessary for composition with existing address selection; it introduces no workload-dependent policy.

`tests/shift-mask.coil` covers 630 scalar and six address fixtures, checking fusion on/off, shared/rooted nodes, zero/oversized/negative-bit-pattern counts, unsupported widths/address types, and unequal counts. All 53,472 native answers match a separate u128 division/multiplication oracle. The final fixture fails its structural assertion on an isolated previous-source tree. Existing arithmetic, address, allocation, PHI and nested native suites pass.

The captured replay replaces ASR+LSL with `and x0,x0,#0xffffffffffffffe0`. Total text remains 1468 bytes because alignment adds one NOP elsewhere; do not claim a code-size reduction. Whole-host seed correctness, broad validation and matched timing are pending. No runtime or generation gain is claimed yet.

The replay generator consumes the lossless snapshot preserved here (decompress it before passing it to `benchmarks/shift-mask/generate.py`). The snapshot generator was the cost-filtered candidate b132cd9e…, and its full object matched 8108f6f0…. The isolated replay does not import complete-module private call masks.

## Full validation before timing

Integration `f5131583` vendors `efc2b64` unchanged. Rebuilt generator SHA-256 is `5b8611c544e86bc9a8c72ab84bc42b8ea907532b220dded3fef2e2bc17e869b5`. The retained-policy host object is `5f73913a63ac15bd1ca0bfd92e21eec38532ff85f8a3d647ab6139aef9a3ecc9`. It emits the fixed seed `9d775276…`, and full-host disassembly confirms AND replaces the shift pair.

All 312 standalone library programs pass, all 73 linked consumers pass with 5,410 fresh private fixture copies, and the freshly linked strength C consumer passes. Standard full FAST passes all 49 steps, including live emission and ASAN checks. Preparation was concurrent, so its time and the printed host-generation duration are not controlled performance measurements. The existing objects-step memory warning remains. Evidence is under `validation/`.

All task-owned build/test jobs finished before fresh warm-ups and the six-round alternating runtime comparison. The source workload remains clean at `892641a250c5ab508134a989eec1c96167b9a250`, source tree `82558967946e5863d28704d93d37704b67d6e1a6`. Timing is pending; no performance claim yet.
