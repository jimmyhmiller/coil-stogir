# Semantic-family outer gate experiment

Base d2ab904. A single mask gate bypasses seven semantic-family checks when
none applies. Opcode44 still enters explicitly. Existing validators, order,
checked counts, and later error overwrites remain unchanged. Overlapping
family bits still execute every matching validator; there is no exclusivity
assumption. This is a verifier source optimization, not an upstream IR fold.

Fixed 93222a58 emitter, common opaque LLVM caller, same 4096-call graph fixture,
eight rotating CPU samples after warmup, compilation finished before timing:
Stogir 445.720→436.9595 ms (-1.97%); LLVM 202.4415→192.683 ms (-4.82%).
Single paired diagnostic, not whole-bootstrap evidence or acceptance. The
whole target remains unmet. Benchmark driver and raw CPU samples retained.

Native O3 suites verify, checked, atomics, terminal, switch, stack, locals and
conversion all pass. Broader differential/malformed coverage, ASAN, repeat
measurement and integrated compiler checks remain required before promotion.
Not installed or pushed.
