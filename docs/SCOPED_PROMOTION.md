# Initial stack-scope promotion experiment

Based on bulk-expansion source `0d6d545`, independently of the validation-sharing
experiment. This remains experimental; no whole-compiler speedup is established.

The existing aggregate splitting and SSA construction follow pinned upstream
`ir_mem2ssa.c` (see NOTICE and PROVENANCE). This additional lifetime eligibility
proof is Coil code, not a claim of full upstream stack-lifetime parity.

The old rule accepts only an uninterrupted ALLOCA prefix before START when a
function contains saved-stack scopes. The new rule also accepts a nonescaping
object later in the initial entry control segment if every memory access follows
its allocation and precedes the first restoration, and every field load follows
a store to that field. Order comes from the existing unique-successor control
index, not instruction reference numbers. Existing prefix objects retain their
original eligibility. Copied/observed stack snapshots, explicit frees, escaping
addresses, overlapping views, and rooted addresses retain existing fallbacks.

Allocations after restoration remain in memory: their addresses can alias older
pointers. The native regression creates an old allocation, restores SP, creates a
fresh allocation, stores through it, and loads through the old address. Eliminating
the fresh allocation would incorrectly erase that observed store. This test also
checks the direct fresh-address load. An uninitialized private load remains a load.

`coil run tests/jit-mem2ssa.coil --debug-checks --sanitize=address` passes. The
positive scoped example emits 84 bytes before explicit promotion and 60 after;
both execute the independent arithmetic oracle over 25 argument pairs. O2/O3
image paths are also exercised. Existing 2115 late-forward cases, 1254 scalar-view
answers, 36 branch-forward cases and observation/partition/barrier checks pass.
The same new positive assertion fails against the original bulk-expansion source.

The new analysis allocates two graph-sized integer arrays plus one cell-sized
array and scans the access index twice. Existing prefix queries are cached per
owner. Integrated compile-time cost and actual compiler-code opportunities must
be measured before considering adoption. No installed toolchain changes yet.

Additional debug-check/AddressSanitizer suites pass: jit-call-frame,
jit-call-stack, jit-sccp-control, jit-aggregate-results, and stack. Captured
logs and exact source hashes are in validation/scoped-promotion.
