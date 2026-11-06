# Callee return SSA preparation checkpoint

The new lowering is not yet connected to native result allocation/emission.
Existing aggregate JIT suite extended with14preparation policies passes with
b27ffeb4 compiler, LLVM O1, --no-debug --debug-checks --sanitize=address,
COIL_LIBRARY_STATE=0. Six supported shapes execute96scalar native probe answers
consuming both promoted words: direct, joined branch, loop-carried, external
write, one-piece and separate return exits. Eight unsupported/observable shapes
retain the buffer path: incomplete initialization, escaped pointer, address root,
x8, HFA, partial store, FRAME_ADDR and raw ALLOCA. Source instruction cells are
compared against a duplicate after each attempt. The full existing aggregate
suite also passes. ASAN instruments the host/harness, not emitted instructions.

The scalar probe explicitly installs a scalar prototype and renumbers ordinary
PARAM ordinals; it tests prepared SSA values, not the final aggregate ABI path.
Initial probe errors (conflicting prototype / patching numeric PARAM ordinal
with a reference-only helper) were corrected; final output above establishes the
result. Final native GP result selection, liveness, parallel copies, frame removal,
JIT/AOT C ABI checks and performance evidence remain required.

A Coil for-field-vector iteration issue is separately recorded in coil-bugs.
