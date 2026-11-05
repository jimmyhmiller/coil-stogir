# Preallocation Phi coalescing — implementation checkpoint

Goal remains whole-bootstrap generation >=5x LLVM O3 and generated compiler
runtime <=1.10x LLVM O3. No performance result is established for this change.

The prepared native pipeline now joins exact-type, same-class, non-overlapping
Phi input/result live ranges before physical allocation, following the pinned
upstream phase. Full hole-aware ranges and sorted constraints are merged;
conflicting fixed requirements reject a union without mutation. Original graph
IDs and definitions survive; aliases share the final split-location index.
Contained COPY/BITCAST reuse excludes these multi-definition groups.

A first pressure run failed three cases with `odd split boundary needs
instruction-specific lowering`. Free allocation could change registers at an
odd definition position. The native allocator now selects partial assignments
using even input boundaries; no emitter guard was weakened. This is distinct
from upstream's still-missing loop-aware optimal split policy.

`tests/phi-coalesce.coil` exhausts 3969 pairs of six-position lifetime sets,
checking exact union, holes, adjacency, overlap rejection and immutability.
It additionally checks conflicting coincident fixed uses, strongest-use merging,
different masks, transitive groups, native-vs-generic split bounds, complete odd
endpoints, and a real scheduled diamond whose overlapping inputs cannot both
join its Phi. The subsequent COPY must remain outside that Phi group.

Native tests use the preserved LLVM-built 88e09ce2 compiler with
`run TEST --debug-checks --sanitize=address` on macOS/arm64.
Passing: phi-coalesce, jit-phi, jit-loop, jit-pressure, jit-switch-pressure,
jit-call-frame, jit-loop-vectorize-stencil, allocation.
Also passing: jit-call-pressure, jit-floating-phi, jit-binary-matrix,
a64-allocate. The initial blanket even-boundary policy failed six call-pressure
cases; explicit sorted call-definition boundaries restore the call emitter's
supported transitions. All four affected suites were rerun and passed after
that correction. The new unit suite checks this exception as well.

Compiler integration, comparative performance and full bootstrap acceptance
remain outstanding. Nothing installed globally.
