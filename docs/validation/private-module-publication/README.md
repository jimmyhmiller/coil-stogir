# Private module publication

The module-bound image entry emits callers without embedding certified leaf bodies.
A context first owns the leaf image bytes and declared ABI under a canonical name.
The target adapter publishes each body once at its original local symbol, confirms
that symbol's actual binding and bytes, then seals the context against a target
scope. Callers must map declarations to the exact published symbol IDs. The
adapter must verify publication before exposing the final artifact. The target
scope and publication borrow their context; neither outlives its owner.

This is distinct from `image-with-private`, which returns a self-contained image
and remains available for standalone consumers. Module publication is not a raw
register-mask override and cannot certify exported, unknown or mutable bodies.

Validation on macOS/AArch64 using Coil candidate71856236:

- `run tests/private-module-publication.coil --backend stogir -O3 --no-debug --debug-checks`: pass.
- The same test with `--backend llvm -O1 --no-debug --debug-checks --sanitize=address`: pass.
- Existing `tests/private-call-allocation.coil` native O3/debug: pass.

The publication test rejects wrong scope, global binding, different bytes,
duplicate target IDs and sealing before all bodies are published. It checks
nonembedding of the callee in a caller image, exact binding identity and rejection
after context release. This does not establish compiler adapter correctness or
whole-compiler performance. Coil integration must supply those separate checks.

Address-taking correction: an emitted FUNC constant with prototype zero is a
valid untyped address, not a typed call declaration. Such references retain the
published name binding without granting a reduced mask. `context-mask` still
requires a validated actual CALL signature matching the owned leaf ABI. Explicit
typed declarations continue to reject mismatches. The module test now covers an
untyped ABS64 address reference; native/debug and LLVM/ASAN both pass. The existing
private allocation/typed mismatch/aggregate suite also passes native O3/debug.
