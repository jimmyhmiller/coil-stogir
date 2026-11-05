# Owned compaction: representation reduction, no useful measured speedup

Library initial1c369bd, compiler candidate7a10f894 versusf50de3b8. The adapter
root audit does not justify weakening existing control observations. Finalized
verifier templates have10057NOPs among25103cells (121templates,40.06%). This is
stored representation, not a profile of NOP time or the entire compiler.

| First comparison median | Before | Compacted | LLVM O3 |
|---|---:|---:|---:|
| IR-codegen ms |120.1210|115.8675|463.9195|
| Runtime CPU ms |35.9675|35.5400|12.7555|
| Object bytes |101090|101090|41440|

Four alternating generation samples and16 rotating runtime samples after
warmups. Generation varied widely; the apparent3.5% reduction is not accepted.
Both Stogir objects are exactly identical. No runtime improvement is attributable
to this storage change.

A separate12-pair alternating-order generation-only repeat after two excluded
warmups per compiler gives before100.849ms/candidate99.165ms as separate medians,
but median paired candidate/before0.991384. Under1%paired improvement does not
establish a useful win. All28objects exactly match SHA256
bc4c18ace8f4f32cc3d637cd8c377ed72b07a512c1b111a1b61fa7efbfa3b171.
Same frozen actual verifier source, serial/O3/no-debug/caches off, all preparation
inside IR-codegen spans, no concurrent build/test during either timed run.
No full bootstrap rerun or backend performance adoption is warranted.

Standalone471a9e5 adds data-only empty instruction namespaces, signed-reference
bounds, and more validation after the frozen compiler experiment. It is not
assigned the prototype's timing result. Debug/ASAN native checks pass for loops,
forward refs, five-argument call continuations, VAR/REG, fixed/ordinary stack,
terminal lists, observed NOPs, scalar/vector pools, embedded-NUL string ownership,
source immutability and construction caches. A switch exercises4-way MERGE and
5-inputPHI, including machine-byte equality. The captured vector stencil also
passes the opt-in O3 path after successful vectorization. Input geometry and
payload/continuation roots reject; a second compaction is idempotent.

Compiler quick PASS62.5s, warning past60s target. Full FAST not run. Compiler
source committed, not pushed or installed. Goal remains5×IR generation and≤10%
whole-bootstrap runtime overhead; latest full diagnostic remains50093aa5 at
2.759560×generation advantage and2.000762×runtime slowdown. Goal unmet.
