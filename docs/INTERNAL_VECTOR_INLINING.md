# Internal vector SSA in scalar-call templates

Eager16-byte streaming45fc238 improved its copy kernel but regressed full
bootstrap generation/runtime and grew matching compiler text by1.08MB. The
inliner rejected any vector LOAD or pure vector value, so otherwise ordinary
scalar/void call templates containing those copies became ineligible. A small
regression executes original byte answers and then fails expected expansion.

Keep existing scalar/grouped parameters and scalar/void returns. Permit normal
supported scalar/vector SSA values for interior pure operations and LOAD/STORE.
Reference/type remapping already clones these operations without changing their
semantics. Budget, Never, private-result, scope, nested-call and guard rules are
unchanged. This does not implement vector call ABIs or expand the opcode set.

Vector LONG_CONST requires more than copying its header: read every payload byte
through checked long-byte, re-intern it in caller-owned storage, and memoize its
head reference in the existing constant map. Nonpointer-lane geometry is equal
at supported pointer widths. Vector-pointer constants retain conservative
fallback; no host pointer width is inferred. Registry snapshots retain complete
constant ownership after external callee storage is destroyed.

Debug/ASAN module-execution suite passes, including384 new original/cloned
native calls over8/16-byte vectors, raw constant XOR payloads,16 alignments,
byte/guard/source checks, Never and zero-budget policies. Registered and direct
APIs agree. Existing vector ABI rejection tests remain. Seven interacting suites
pass: inline-stack-results, jit-bulk, jit-bulk-pressure, jit-mem2ssa,
jit-sccp-control, static-stack and validation-transaction29700 comparisons.
An independently linked C AOT caller validates all16 alignments, constant bytes,
return value and memory guards on the inlined16-byte result image.

Logs, independent caller, assembly and hashes are in validation/internal-vector-
inlining. Compiler integration and recovery of the full-bootstrap regression
remain unmeasured; no performance acceptance or global installation claim.
