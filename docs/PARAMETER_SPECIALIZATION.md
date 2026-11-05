# Context-bound numeric parameter specialization

The actual verifier trace records23 initially eligible sites and15 expansions,
with generic string-equality calls remaining in its loop. Budget pressure is a
hypothesis; this module does not establish that it explains the runtime gap.

`parameter-specialize.specialize` takes an immutable source graph, roots and
explicit numeric bindings to positive entry PARAM references. Original graph
validation happens before edits, so replacing a PARAM cannot hide malformed
source storage. A private duplicate receives same-type zero-flag COPYs at those
references; the existing checked SCCP pipeline owns the next analysis epoch and
preserves/remaps supplied roots. No new folding semantics are introduced.

The owned `Specialized` artifact carries its rewritten graph, numeric argument
conditions (ordinal, type, exact bits) and target pointer width. Its body is
equivalent only under all attached conditions, not for arbitrary arguments.
It must never be registered as an unconditional alternate definition. The
`bindings-match?` predicate checks literal arguments and target width only;
ordinary callee identity, complete prototype, Never, recursion, closed-control,
private result/capture and exact inline-growth proofs remain required. Source
and artifact storage are distinct and all failure paths release partial work.
Only valid same-type numeric scalar literals are supported. Dynamic values,
positive expressions and named relocation payload IDs do not satisfy conditions.

The native reduction has nested equality branches and an observable STORE on
the equal/nonzero path. Binding one U64 parameter to zero removes that path.
The source still performs the STORE for other equal arguments; native canaries
and returned values check both behaviors. The source PARAM remains unchanged.

Existing exact inliner preflight reports17 minimum clone cells for the original
and8 for the specialized callee. With a budget of8 the ordinary callee is rejected,
while the checked specialized callee expands and the native caller returns correct
answers for32 inputs. The caller's budget is not raised or replenished.
Debug/ASAN tests cover changed/dynamic actual arguments, wrong target width,
empty/duplicate/non-PARAM/missing bindings, malformed original arity, invalid
roots, unsupported pointer width and a32-bit pointer payload overflow.

This is an independent context-specialization extension over the pinned compact
IR and existing SCCP. It is not upstream feature parity. Attribution remains
in LICENSE/NOTICE/PROVENANCE. It is not yet wired into ordinary inlining or Coil;
no compile-time or bootstrap runtime improvement is claimed. Integration still
needs a bounded cache tied to immutable callee identity and exact binding
conditions, preserving original validation and one nonreplenishing clone ledger.
Avoid one whole-callee optimization per call site; measure preparation overhead.


## Verified actual budget pressure

Diagnostic compilereda0391c adds reserved/remaining cells to existing verbose
inline tracing, without changing inline policy. Its actual verifier expansion
reserves509 of512cells over15 of23sites, leaving3cells. The string-equality
callee has32 base clone cells. The verifier object is byte-identical to the
88e09ce2 baseline. This verifies budget pressure rather than merely inferring
it from surviving calls; it does not show specialization's eventual runtime
or preparation cost. Trace and hash receipt are retained with validation.

The native budget reduction also passes with extra branch/control observations
retained alongside RETURN, as compiler templates do. Ordinary inliner identity,
closed-control and exact-budget checks still pass, with minimum17→8cells.
