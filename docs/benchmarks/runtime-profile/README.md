# Current-host dynamic profile refresh

The latest loop transformations change local machine code but have not closed the whole-workload gap. Refresh the dynamic profile before choosing another transformation. The initial comparison is between fresh regional, strength, and hoisting-plus-strength hosts, so additional loop-carried values can be traced to their dynamic costs.

`prepare.py SOURCE OUTPUT` copies the compiler sources into a new diagnostic directory and adds block counters there. Production sources and the existing audit worktree remain untouched. The only compiler changes are a diagnostic module, one emission hook at physical block labels, and adapter hooks to enable counting and identify functions. Without `COIL_STOGIR_BBCOUNT=1`, the emitter adds no instructions; validate byte identity against the ordinary control host.

Each counter uses reserved x16/x17 and six instructions that preserve NZCV. A separate dylib maps a 64 MiB array at the requested address using a non-destructive mmap hint, refusing a different address. The source refuses counter indices beyond that extent. Counting requires serial execution. Both the generator and counted host load the runtime, because native compiler helpers can execute while the generator emits code. Counter hosts are diagnostics, never cycle-timing evidence.

Validate each counted host by emitting the unchanged fixed compiler workload and requiring seed SHA-256 `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`. Preserve generator/host identities, the map, counts, and disassembly. Decode with the existing `mixdump.py` tooling from the integration checkout; copy the exact tool used into the evidence directory.

Physical block execution counts are exact for the serial run, subject to 64-bit counter overflow not occurring. Derived instruction mixes are estimates: emitter-created branches/stubs and prologues lack independent counters, and code after unconditional terminators is excluded. Do not equate their sum with the hardware instruction count. Profile counts guide investigation only; no measured weights or workload identifiers enter production policy.

## Completed diagnostic

All three counted hosts emit the fixed seed. The disabled instrumentation host reproduces the ordinary fresh regional object exactly. Source identity and generator/host hashes are in `evidence/results.json`. The original complete disassemblies remain in integration `build/runtime-profile/current/`; maps, counters, derived mixes, tools and ranked deltas are archived here. No production hooks were added and the old audit worktree was not accessed.

| Host | Estimated counted instructions (B) |
|---|---:|
| Regional | 188.395 |
| Strength | 191.575 |
| Hoisting + strength | 190.425 |

The dominant new regression is `coil.compiler.closure.closure-subprogram-scoped`: +1.514B estimated instructions in both strength configurations, from 2.525B to 4.038B. Its hottest search body runs about 289M times. Previously it loaded the array pointer, used `add index, lsl #4`, and loaded two adjacent words with LDP. Strength reduction adds an offset recurrence, entry/back-edge moves and a hot reload; the two data loads also cease to pair. These are actual annotated machine instructions, not a hypothetical graph cost.

Other combined increases include assigned-indexed-pressure (+0.344B), pressure-class-into (+0.221B), string hashing (+0.155B), and register liveness (+0.117B). Conversely, the intended lookup loop improves by 1.134B and primitive-providers by 0.317B. The local success is real but outweighed by other transformed loops. Derived totals remain estimates, with the coverage limits above; they are not substituted for measured cycles.

## Target-cost follow-up

The generic affine pass now accepts a product-profitability predicate, evaluated on the current immutable graph each batch. The unrestricted entry point retains its existing proof/test behavior. The AArch64 wrapper queries the existing arithmetic selector and accepts only products selecting its actual multiply rule. Constant powers of two and 2^k+1 already select shifts/shifted ADD and do not alone justify another carried value. They can still be part of an affine expression that also removes a real multiply. No profile weights, function names, strides or source references enter this policy.

Expanded tests cover 88 constant-product fixtures across signed/unsigned 32/64-bit words, both operand orders, cheap scales and real multiplies. They check that the unrestricted proof admits every fixture and the target accepts only the costly cases; native execution uses the independent modular oracle. Together with existing arithmetic fixtures, 207,360 native executions pass. Alternate existing fixtures exercise the target callback with variable products, mixed products and shifted expressions. Nested integrated native and C-linked cases pass. The full-workload cost-filtered hosts have not yet been measured.


## Integration and next comparison

Library `0a79472`, integration `da68ff43`: sources match exactly and the candidate rebuilt. The preserved generator is integration `build/loop-strength/cost/measured-candidate` (identity in `generator.json`). Fresh disabled-control, strength, combined strength/hoisting hosts and quick FAST are preparing. These are concurrent preparation, not generation benchmarks. The captured stride-40 replay remains 308/296/308/284 bytes, retaining the earlier useful loop shape.

After all preparation is terminal, require the disabled control object to match `views/regional/host.o`; separately verify both new hosts emit the fixed seed. Then compare LLVM, fresh regional, previous unrestricted strength and combined hosts, and the two cost-filtered hosts in three serial alternating rounds. Preserve all outputs and timing samples. This profitability gate only excludes already-cheap products; it is not a complete register-pressure cost model and has no measured runtime result yet.
