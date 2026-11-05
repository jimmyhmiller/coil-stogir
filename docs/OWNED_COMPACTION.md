# Owned instruction compaction experiment

The actual verifier dependency trace contains121 finalized templates with25103
physical cells,10057of them NOPs (40.06%; denominator includes sentinels). For
example graph.operand has93NOPs in272cells. This measures stored representation,
not time spent on NOPs or the entire compiler. The adapter already observes
returns/nonreturning cycle edges and removes pure observations at key boundaries;
no evidence justified weakening its root contract.

compact creates an independent graph epoch and old-positive-header→new-reference
map. Only NOPs without reference edges or explicit observations are removed.
Complete extents are copied before operand rewriting; every reference category
from the packed schema is remapped, including terminal membership, labels,
guards and VAR/REG. Negative constant IDs, complete constant payloads, string IDs
and function prototype IDs remain unchanged. Referenced/observed NOPs survive.
Continuation cells and removed headers map to0. Positive expression caches are
cleared; constant/string construction indexes retain their unchanged namespaces.
The source graph, references, roots and facts remain intact. Both source and
output receive full validation, so this pass cannot conceal malformed input or
transport stale analyses. It does not perform dead-operation elimination.

This is an independent Coil storage extension; pinned upstream uses stable NOP
rewrites and no equivalent compaction stage was found. It is not upstream parity.
The native image-compacted-with-options entry point is opt-in. At O2/O3 it runs
after scalar/vector rewriting, before fresh CFG, matching and allocation. The
owned graph lives through image serialization, shared by JIT and AOT; default
image-with-options policy is unchanged. All entry/roots are remapped explicitly.

Native debug/ASAN tests cover signed loop backedges/forward Phis, an indirect
five-argument call with continuation storage, ordinary and fixed stack storage,
terminal-list links, a retained NOP root, long vector constants, constant interner
reuse and cleared expression caches. Every mapped operand is checked against its
schema role, headers/arity/constant payloads are checked, and source immutability
is checked. Switch cases cover4-way MERGE and5-input PHI extents; native results
match and original/compacted switch machine bytes are identical. Old and opt-in
image APIs execute across O1/O2/O3. Invalid roots, pointer width and malformed
original CALL geometry reject before edits. Performance remains unproven.


Additional checks preserve empty instruction namespaces with constant roots,
reject continuation/payload roots, exercise VAR and REG operands across a C call,
verify idempotence, and read embedded-NUL string data after the compacted graph
has been released by the native image API. The captured stencil adds the opt-in
O3 mode, exercising successful vectorization before compaction and native results.
A signed-reference bound guards construction of retained positive headers.

Compiler experiment7a10f894 pins the initial1c369bd pass. Its four-sample median
looked3.5%lower but varied widely. A12-pair alternating-order generation repeat
after excluded warmups yields median paired candidate/baseline0.991384; before
100.849ms versus candidate99.165ms as separate medians. All28objects have the
same SHA256bc4c18ace8f4f32cc3d637cd8c377ed72b07a512c1b111a1b61fa7efbfa3b171.
This establishes byte-identical output, not a useful compile-time speedup.
No runtime improvement is attributable to compaction and no backend adoption is
justified. The later empty-namespace/bound correction is standalone only; no
performance number is assigned to it. The whole-bootstrap goal stays unmet.
