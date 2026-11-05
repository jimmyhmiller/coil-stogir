# Owned memory pipeline experiment — not adopted

Explicit `sccp/optimize-memory!` permits forwarding/promotion on caller-owned
mutable input, returning an independent optimized graph. The immutable API
retains its input-preservation contract. Both share validation and pass order;
private helpers cannot be imported. This is Coil ownership orchestration around
the existing pinned upstream memory-before-SCCP pipeline, not a new upstream pass.

Expanded jit-mem2ssa debug/ASAN tests compare raw graph words, roots, constants,
string bytes and generated native text, and release mutable input before output
code generation. Six fixture policies cover 4/8-byte pointers and both endian
settings; invalid combinations must produce identical diagnostics. Native
execution and existing memory forwarding/control tests pass, as does the
existing iterative fold suite. Command: frozen e450d4a9 candidate,
`COIL_LIBRARY_STATE=0 coil run tests/jit-mem2ssa.coil --backend llvm -O1
--no-debug --debug-checks --sanitize=address`, likewise jit-iter-fold.coil.

Small timing fixture: benchmarks/compiler-gaps/owned-memory.coil, LLVM O3
no-debug build, same candidate. Sixteen alternating samples after warmup.
512-operation graph: immutable151.5us, mutable152.5us.
2048-operation graph: immutable601.5us, mutable600us.
These differences are below1%; no demonstrated speedup. No compiler worktree
was changed or built for this API. Preserve as a tested experiment; not adopted
as an optimization toward the whole-compiler target.
