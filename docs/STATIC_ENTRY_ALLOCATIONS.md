# Fixed function-lifetime objects: first stage

This is incomplete performance work, based on bulk128 source0d6d545. No compiler
integration or bootstrap speedup is claimed. The virtual address definition and
its ordinary register interval are deliberately still present. Removing that
interval and rematerializing the address in all consumers is the next stage.

## Semantics and provenance

Pinned ir_aarch64.dasc selects IR_STATIC_ALLOCA for numeric constant ALLOCA in
entry block1 under IR_FUNCTION; fixed objects have frame offsets and addresses
can be rematerialized. The port previously emitted every ALLOCA as an SP change.

An initial unconditional conversion failed572 of the2640 existing stack checks:
zero-sized ALLOCAs observe raw SP and relative object distances. That conversion
was removed. Existing tests and raw-stack behavior are retained.

`builder/frame-object!` explicitly declares a positive constant-extent,
function-lifetime object in the entry allocation prefix. It uses ALLOCA's existing
operand layout and auxiliary32768 as an independent semantic attribute. This
attribute is Coil code, not upstream metadata compatibility. Ordinary ALLOCA
retains its original raw-SP meaning. Frame objects do not contribute to AFREE
or saved-SP scopes. Their physical position relative to raw SP is unspecified.
The native validator checks the marker, extent, entry prefix, type and alignment;
the builder rejects invalid requests without appending a node.

Call cloning clears this attribute and lowers the callee's object to call-local
storage inside the existing explicit save/restore scope, preserving bounded
caller stack use. The million-iteration native inline-result loop exercises this
path. The opcode and cell format remain unchanged. Attribution remains centralized
in LICENSE, NOTICE and PROVENANCE.

## Native pipeline

Matching records an immutable graph-reference-indexed size plan before liveness.
Frame layout allocates distinct checked aligned local slots, separate from spills
and outgoing arguments. Static definitions materialize the frame-relative address
in their ordinary assigned GPR; they do not change SP. Dynamic storage still
establishes the anchored frame and follows the original lowering. Compatibility
allocation entry points select the same object plan.

This stage does not yet remove GPR pressure from object addresses. Future work
must represent rematerializable frame addresses in machine uses, constraints,
locations and all call/edge/return transfers. A frame address is not the contents
of a spill slot. No location check or required-register constraint may simply
be bypassed.

## Validation

Debug checks and AddressSanitizer pass the new selection/native matrix: fixed
objects, distinct objects, variable counts, nonentry raw allocations, zero size,
8193-byte/64-aligned storage, saved scopes after fixed storage, and mixed fixed
storage with dynamic allocation/free. Native results use an independent x+13
oracle. The same8193-byte object is emitted as Mach-O, linked by cc and checked
from C on8 inputs including unsigned wraparound.

Existing suites pass: stack builder/errors,2640 raw nested stack cases,
jit-stack-scopes, jit-stack-branch, jit-stack-loop, jit-call-stack,
jit-frame-address, jit-local-frames, jit-locals, jit-bulk-pressure,
jit-aggregate-results, inline-stack-results, and verify. Bulk pressure now covers
both raw and fixed objects with calls and spills; inline result cases cover both
storage declarations. Logs, C caller, assembly and source hashes are archived in
validation/static-entry-allocations.

The native pipeline additionally rejects forged markers with nonentry control,
variable or zero extent, unknown marker bits and wrong result type. Constructor
rejections preserve graph length; tests mutate headers directly to exercise the
validator independently of the checked builder.
