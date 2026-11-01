# Control flow

The graph retains the upstream Sea-of-Nodes control model. Block starts and
terminators are graph nodes; CFG analysis, placement, scheduling, allocation and
edge reconciliation run before target emission. JIT and AOT use the same lowering.

## Integer switches

`builder/switch!(graph, control, selector)` emits SWITCH and ends the current
control chain. The selector must be an integer/address scalar value, not a VAR
storage identity. Case blocks start with these checked builders:

- `case-value!(graph, switch, constant)` matches one value.
- `case-range!(graph, switch, low, high)` matches an inclusive interval.
- `case-default!(graph, switch)` handles values outside the explicit cases.

Endpoints must be numeric constants of exactly the selector type. Signed values
use the type's signed order, including CHAR's signed byte storage. BOOL endpoints
are zero or one. Ranges cannot wrap or reverse; a signed interval from -1 to zero
is valid, while one from the signed maximum to the signed minimum is not.

Builders check local shapes and types before mutation. Complete-dispatch
validation additionally requires exactly one explicit default and disjoint case
intervals. Duplicate values, intersecting ranges, non-case SWITCH successors and
malformed raw nodes are rejected. All case/default exits must participate in the
compilation's observable roots. Omitting a projection is diagnosed rather than
silently producing a branch to an unbound target.

Case blocks may have normal memory operations, calls and further control flow.
Use END nodes to feed a MERGE and PHI nodes for case results. The order of PHI
inputs follows MERGE predecessor order, independent of dispatch sorting. Loop
backedges use the existing LOOP_BEGIN/LOOP_END and loop-phi construction.

## AArch64 dispatch

Case intervals are heapsorted in O(n log n) time with bounded extra sorting
storage. Flipping the storage sign bit maps signed values to unsigned order keys
without overflow. Selection normalizes the selector into reserved x16; comparison
constants use x17. Balanced comparisons give O(log n) dispatch depth for sparse
cases and ranges. Default-only dispatch is supported too.

Dispatch branches to a separate stub for each case/default. Each stub reconciles
ordinary live values before entering its block. Comparisons finish before any
edge copy can overwrite a scratch register. The usual parallel-copy machinery
handles GPR/SIMD/spill values and subsequent merged-result phis. Fixed and dynamic
stack storage keep the same anchored-frame semantics as other branches.

Dense jump tables and dispatch-strategy measurements remain unfinished. Internal
branches currently use the existing checked AArch64 immediate fixups; general
long-branch relaxation is also unfinished. These limitations are not performance
claims. Full compiler integration and LLVM/TPDE comparisons remain delivery gates.
