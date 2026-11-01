# Darwin AArch64 scalar ABI

The standalone backend currently targets macOS AArch64. Function graphs and callee
annotations retain binary prototypes in the graph-owned string table. The layout
follows [Apple's ARM64 ABI](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms).

## Declaring a function

Use `calls/create` to construct a scalar prototype, then
`calls/function!` to attach it to the graph. The graph owns a serialized copy;
release the construction-time prototype with `calls/release!` afterwards.
Declaring the same prototype again is allowed; a conflicting declaration errors.

`PARAM` operand 3 is the **source parameter ordinal**, starting at zero. It is
not a physical register number. A declared signature allows unused projections
to be omitted while preserving the types and positions of all parameters.
The projection's type must agree with the declaration, and each ordinal has at
most one projection. Its region must be the function entry.

For graphs without an explicit declaration, the backend infers a signature from
all PARAM nodes before liveness removes unused projections. That requires a
complete prefix of parameter types through the highest projected ordinal. A gap
produces a diagnostic asking for a declaration; it does not guess a missing type.

The existing `calls/attach!` API annotates a callee address with a PROTO node.
It is separate from `calls/function!`, which describes the function being built.

## Locations and lifetime

Integer, boolean, character, and address parameters use x0–x7 in integer-argument
order. Floating parameters consume their own d0–d7/s0–s7 locations. The classifier
accounts for unused floating parameters, including their stack slots. Live f32/f64
parameters and results now use SIMD allocation, typed incoming stack loads and
exact-bit constant return materialization. Incoming register reservations cover
both banks, and entry PARAM capture precedes calls even when constructed later.

Once a scalar class exhausts its eight argument registers, fixed stack parameters
use their natural size and alignment. Signed byte/halfword parameters load with
sign extension; unsigned and boolean values load without sign extension. Pointer
parameters occupy eight bytes. Incoming stack offsets are relative to entry SP,
so emission adds the finalized local frame size after the prologue adjusts SP.

Block starts and parameter projections precede body instructions in each block's
schedule. Physical reservations protect incoming GPR values from entry until
capture, including when earlier stack projections need registers. Calls reserve
caller-saved registers; live-through values spill. Non-leaf functions link and
restore a frame record containing x29 and x30.

Outgoing call arguments use a separate area at current SP below spill slots and
the non-leaf frame record. Darwin integer variadic calls place unnamed promoted
values in aligned eight-byte slots after the fixed arguments. The outgoing-area
planner and emitter share the same layout model. Sub-32-bit register arguments
are sign/zero-extended to 32 bits after simultaneous copies consume their sources.
Fixed stack arguments use byte/halfword stores where appropriate; unnamed narrow
integers are promoted before their eight-byte variadic slots. Narrow call results
and generated function results are normalized by signedness.

A void RETURN uses zero for its absent value operand. Non-void RETURN requires a
value of the declared type. The builder, patcher, structural verifier, semantic
verifier, and emitter agree on that distinction.

## SIMD scratch

Integer population count uses v31 for scalar transfer, CNT and ADDV. v31 is
caller-saved under the current Darwin target and is reserved for emission,
consistent with the [AAPCS64 SIMD register convention](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst#simd-and-floating-point-registers).
The SIMD allocation mask now excludes v30/v31, preserving v31 for this
sequence and reserving two floating emission temporaries. Scalar numeric conversion and truth/selection now use these reserved
temporaries. Vector lowering remains incomplete. No callee-saved SIMD
registers are changed.

## Current limits and evidence

Incoming live integer scalars, including byte/halfword values, bool, char, and
pointers, have lowering. Native coverage includes mixed 32/64-bit stack slots,
narrow sign/zero extension, a stack pointer parameter, omitted projections,
reversed projection order, and unused floating arguments. A separate regression
constructs a call before a register PARAM and verifies capture before clobber.
The mixed stack/non-leaf function also links and runs as AOT code. Narrow binary
operations and comparisons normalize operands locally and preserve original live
values. The 24-value call-pressure test includes signed byte/halfword values
widened for a call and then stored from their original SSA values after the call.
Even-position reloads run before odd-position pre-clobber spill stores; each
subposition remains its own parallel-copy group.

Outgoing calls support scalar integer, bool, char, address, f32 and f64 arguments
and results, plus void/narrow results and Darwin integer/floating varargs.
A shared per-argument plan assigns GPRs and FPRs independently, packs exhausted
fixed arguments at natural sizes, and puts unnamed promoted arguments in
eight-byte stack slots. f32 variadic values convert numerically to f64. JIT and linked AOT checks exercise a
sixteen-argument callback with narrow register/stack permutations, signed and
unsigned return boundaries, variadic promotion through libc snprintf, and a
non-leaf void-returning function. A native callee probe reads the already-extended
32-bit argument register, detecting missing extension of negative constants.

Further control/intrinsic semantics, reading variadic function arguments, aggregate ABI
lowering, other conventions, additional special constants, and additional
AOT formats/features remain unfinished. Named FUNC calls and FUNC/SYM/STR
addresses now lower through shared image relocations, including recursive calls. See [IMAGES.md](IMAGES.md) for the shared
image relocation support. Unsupported cases must produce explicit diagnostics. ABI coverage is
not a claim of full upstream parity or measured compile/runtime performance.

## Register-class and transfer foundation

Allocation parts now carry admissible physical-register masks, preserved across
splits and enforced by both allocation decisions and independent checks. Target
physical IDs are GPR 0..31 and SIMD 32..63. The AArch64 bridge retains 16-register
scans for GPR-only functions and can represent mixed classes without assigning
floating values to GPRs. Live floating PARAM/RETURN/call ABI is now connected to this foundation.
Floating arithmetic, memory, bitcasts and phi constants now have selection.
Numeric conversions and scalar truth/conditional selection now have lowering;
remaining control/intrinsic semantics still prevent full-library parity.

Allocatable GPRs remain x0..x15. The SIMD mask admits v0..v7 and v16..v29;
v8..v15 are excluded until callee-save preservation is implemented. v30/v31 are
reserved for floating emission, and integer CTPOP also uses v31. GPR scratches
x16/x17 remain separate from these SIMD registers.

Physical scalar transfers support GPR, SIMD and stack locations, including raw
32/64-bit moves between banks for bit reinterpretation. Parallel-copy resolution
uses disjoint register and spill-location encodings and preserves payload bits
through mixed cycles. Target frame copies hold their cycle temporary in reserved
v31, with x16 for addresses and x17 for memory data. Raw FMOV transfers do not
numerically convert values. The legacy immediate-only API can still use a GPR
cycle temporary. SIMD loads/stores and transfers
preserve NZCV. Failed transfers do not partially append code bytes.

## Floating ABI evidence

Native tests cover all eleven FP source ordinals (d0/s0 through d7/s7, then three
stack positions) for both widths, exact NaN/signed-zero returns and constants,
and incoming values retained across a non-leaf call. The latter deliberately
constructs the call before the PARAM projection and verifies capture first.
Mixed calls carry ten integer and ten alternating f64/f32 arguments, exhausting
both banks and exercising natural stack packing. Checks cover floating results
and live-through values in either bank, including an integer retained across an
FP-result call and an f32 retained across an f64-result call. Linked objects
exercise mixed calls, stack inputs above the non-leaf frame, and snprintf default
floating promotion. Arithmetic/comparisons, memory, live bitcasts and phi constants now pass native
and linked tests. A 24-value FP call-pressure test covers both widths and forced
SIMD spills. Numeric conversions and scalar truth/selection now have native and linked
coverage. Wider compiler/intrinsic/control semantics remain separate gates.

## Numeric conversion and truth contract

INT2FP uses source storage signedness and width, normalizing narrow sources into
scratch before SCVTF/UCVTF. Integer-to-f32 folding converts directly to f32; it
never routes through f64 and therefore avoids double rounding at 64-bit integer
midpoints. FP2INT rounds toward zero. Folding decodes IEEE sign/exponent/fraction
bits with integer arithmetic and folds only when the truncated result fits the
destination storage range, including negative fractions that truncate to unsigned
zero. NaN, infinity and out-of-range truncated values stay unfolded; native AArch64
instruction behavior outside that domain is not a portable conversion promise.
Narrow results normalize to their storage width. Boolean results are canonical
0/1 after byte-width integer conversion, distinct from testing FP nonzero truth.

FP2FP is an exact identity at equal types. Precision-changing finite conversions
use FCVT; constant NaNs remain unfolded so the target handles payload processing.
Scalar folding assumes the normal default rounding environment; explicit FP
environment control and observable exception flags are not represented by these
pure IR operations.

IF and COND share typed truth flags: either signed floating zero is false, NaNs
are true, and integer/address comparisons use their full declared width. COND
captures flags before literal materialization and chooses CSEL or FCSEL according
to the result bank. Typed arm materialization preserves flags and raw payloads.
LLVM i1 casts and signedness-specific LLVM conversion opcodes require explicit
frontend lowering rather than blindly using the IR Boolean storage byte.

## Scalar local storage

`builder/variable!` creates a named VAR in a block-start region. Its scalar type
sets the object size. Alignment zero means natural scalar alignment; explicit
power-of-two alignment is in bytes. The AArch64 target selects a frame alignment
A equal to the maximum of sixteen and selected VAR/ALLOCA requests, then aligns
the actual SP to A. Relative slot alignment therefore establishes actual address
alignment even when the caller guarantees only sixteen bytes.

`builder/variable-address!` creates an ADDR-valued VADDR. VAR itself denotes
storage and cannot serve as an ordinary register-value operand. It contributes
graph dependencies without creating a register interval. VLOAD/VLOAD_v use
`[control variable]`; VSTORE/VSTORE_v use `[control variable value]`. Access types
may differ from the declared storage type when their scalar size fits the object.
Volatile variants remain explicit control-chain operations. Objects are not
automatically initialized.

Fixed outgoing arguments, the non-leaf frame record, local objects and spill
slots occupy disjoint frame storage. Local objects and spilled values have
separate ownership maps, so equal owner IDs cannot cause accidental aliasing.
Local addressing handles offsets beyond ADD-immediate encoding. Native coverage
includes all scalar types, mixed storage views, literal/volatile accesses,
alignment, integer/FP loops, 24 local addresses live through a mutating call with
forced spills, and 1,100 local objects in an 8.8 KB frame. Linked objects cover
Boolean/integer/floating storage, loops and the large frame.

Large scalar spill and outgoing-call offsets have explicit address materialization
as described below. Over-aligned frames use saved entry SP as described next.

## Anchored fixed frames

`builder/frame-address!` emits ADDR-valued FRAME_ADDR. The current target policy
establishes a real x29 frame record whenever this operation is selected, even in
a leaf function. FRAME_ADDR returns that record address. Its first eight bytes
hold the previous x29 and the next eight hold saved LR. This policy selects the
upstream frame-pointer case rather than its entry-SP fallback.

`frame-address/Base` records the physical base and logical anchor offset. Fixed
storage lowering uses SP/zero bias for ordinary functions, or x29/frame-record
bias for anchored functions. The context reaches split/parallel transfers, phi
edge stores, incoming arguments, locals and call operand capture. Outgoing call
argument stores use current SP. Existing low-level emission APIs retain their
SP-based behavior; their `-at!` forms accept an explicit frame base.

Frames with A greater than sixteen add a saved original entry-SP field at x29+16
and reserve a 32-byte record. The prologue captures entry SP in x16, subtracts the
fixed frame using x17 when a scratch is needed, then aligns SP down through x17.
Frame-record stores preserve x16 until its saved slot is installed. Incoming
stack arguments load through that saved pointer rather than assuming a constant
entry-to-frame displacement. `incoming/emit-entry!` provides this low-level path;
the existing `emit-at!` path retains the constant-displacement behavior.

At every anchored return, fixed SP is restored from x29 before the saved frame
registers are loaded. Over-aligned returns retain saved entry SP in x17 while x16
addresses the record, then restore SP exactly, including alignment padding.
Native tests verify prior-frame linkage and saved LR,
both scalar widths and register classes under forced spills, incoming stack
parameters, FP phi cycles and local storage in ordinary and anchored modes.
A separate native test moves SP by 256 bytes and verifies GPR/SIMD/memory
parallel-copy cycles through the fixed anchor. Dynamic ALLOCA/AFREE now use this
anchor and the outgoing-area policy below.

## Dynamic stack objects

`builder/stack-allocate!` emits ALLOCA with control, integer byte-count value and
alignment metadata. `builder/stack-free!` emits AFREE with control and byte count.
Both use the same `round_up(count, A)` size, where A is the function frame
alignment and is at least sixteen. Counts can use any scalar integer
storage type, including ADDR. Signed counts must be nonnegative; all counts must
be at most `i64::MAX - (A-1)` so rounding fits. Construction checks constants using
the request's known minimum alignment; target lowering rechecks against the final
function alignment. Dynamic counts normalize their declared width/signedness
and trap before allocation/free changes SP when outside that domain. Available stack capacity
remains a platform limit.

Alignment zero requests the sixteen-byte minimum; larger power-of-two requests
raise the function's alignment. A zero-size operation moves SP by zero. AFREE must match the byte
count of the most recent live allocation; its original unrounded count is valid.
Function return restores the frame anchor and discards any remaining objects.

Every function with ALLOCA/AFREE uses x29 for fixed storage. Let N be its maximum
outgoing argument area, rounded to A. `[SP, SP+N)` stays reserved for calls.
Allocating d rounded bytes subtracts d from SP and returns `SP+N`. The new object
occupies `[newSP+N, oldSP+N)`, below older objects and the anchored frame record.
Outgoing stack arguments therefore cannot overwrite live dynamic data. Fixed
locals/spills and incoming stack parameters remain independent of current SP.

Native checks cover one thousand size/type/alignment/nesting variants, both
freeing and return-only restoration, invalid-count traps in isolated children,
24 dynamic addresses live through a mutating call with forced spills/outgoing
stack arguments, FP pressure with a live dynamic count freed after the call,
incoming arguments, integer/FP memory-state loops with changing allocation sizes,
and distinct returns at different stack depths. Linked objects cover dynamic
call objects, both loop result classes and branch-dependent restoration.

Over-alignment evidence includes 1,664 scalar local-storage variants through 4 KB,
2,640 nested allocation/free variants through 8 KB, large aligned GP/FP call
pressure, and an external callback checking 24 dynamic addresses at 4 KB alignment
with the outgoing area expanded to match. A separate caller sweeps all 278
sixteen-aligned entry-SP positions modulo 32/64/256/4096 and checks incoming
mixed-width stack values, fixed/dynamic addresses, calls, free and exact SP
restoration. Linked 64-byte and 4 KB frame fixtures execute too.

## Large scalar frame accesses

`a64.frame-memory/access!` first tries the direct scaled load/store encoding,
then materializes an address in a caller-owned GPR when necessary. It handles
integer byte/halfword/word/doubleword accesses, signed narrow loads and f32/f64
accesses, including unaligned views. Address construction and memory operations
preserve NZCV. Incoming stack arguments, outgoing stack stores and saved-frame
record accesses use this path.

`transfers/emit-addressed!` accepts separate data and address scratches for large
register/memory and memory/memory copies. `transfers/parallel-frame!` reserves
v31/x16/x17 for cycle/address/data values so address materialization cannot
destroy a live copy-cycle temporary. It remains valid when SP moves under an
anchored function. The solver uses dense stack identities mapped to i64 byte
offsets, rather than casting offsets into its i32 move IDs. The legacy low-level
immediate-only APIs retain their explicit range diagnostics.

Native tests cover direct-encoding boundaries, unaligned offsets through 65 KB,
surrounding-byte integrity, signed loads, exact FP payloads and preserved flags;
distant mixed GPR/SIMD/memory cycles; and whole functions with 4,200 fixed objects
pushing GP/FP spills and incoming arguments past immediate ranges. Offsets beyond
i32 are checked for emission only. A 4,105-argument variadic call exercises a last
stack argument at SP+32768 and a still-higher frame record, with/without a live
dynamic object, through JIT and linked AOT.

Fixed prototype parameter counts retain the upstream one-byte limit of 255.
Total CALL inputs use sixteen bits: after control/callee, up to 65,533 actual
arguments are representable. Variadic call construction now distinguishes those
limits; boundary tests reject excess counts before graph mutation.

## Dynamic stack scopes

`builder/stack-save!` emits upstream BLOCK_BEGIN, a control-pinned ADDR result
containing raw SP. `builder/stack-restore!` emits BLOCK_END and restores that
pointer. A restore releases all allocations after the snapshot, so their sizes
need not be available. Both operations require a control predecessor that has
not ended its block; restore additionally requires an ADDR value. A VAR storage
identity is not an address value.

The saved pointer includes the outgoing argument prefix. Do not adjust it by
`outgoing-size` or treat it as an ALLOCA object address. Snapshots are ordinary
allocated values and may spill across calls; fixed-frame slots stay relative to
x29. Save/restore-only functions also establish a frame record. Both instructions
preserve condition flags.

The caller must use a live snapshot from the same function invocation, preserving
its stack/frame alignment, and must stop accessing objects released by restore.
The IR does not insert runtime provenance checks on saved pointers. Whole-function
return restores the entry stack regardless of remaining dynamic scopes.

## Indirect aggregate arguments

`builder/argument-value!(graph, source, size, alignment)` emits the reference
ARGVAL node: an ADDR result with an ADDR source and signed i32 size/alignment
metadata. Size must be nonnegative. Alignment may be zero (natural minimum) or a
positive power of two. The AArch64 private copy has at least eight-byte alignment;
requirements above sixteen also raise the function's actual frame alignment.
A VAR identity is not an address; use VADDR. ARGVAL cannot wrap another ARGVAL.

ARGVAL is only valid as a CALL argument. Declare that prototype parameter ADDR.
At the consuming call, the object is copied into private caller storage and the
copy's pointer is passed using the ordinary integer bank or stack pointer slot.
Incoming indirect parameters are normal ADDR projections. A preceding
control-ordered write is visible in the copy. The callee may mutate its copy
without changing the source. Reusing one ARGVAL node in several argument
positions creates distinct copies; each call refreshes its copies.

Private buffers follow all scalar stack arguments in the outgoing area, with
checked alignment and size accounting. Consequently they are distinct from
fixed locals/spills and live dynamic allocations. Calls may reuse the outgoing
area, and a pointer to a copy must not outlive that call. The source must denote a
readable normal-memory range of the declared size and must not alias internal
outgoing storage. A zero size performs no source access and reserves a distinct
aligned byte for the private pointer. Available native stack space remains a
platform limit.

The copy emitter uses exact eight/four/two/one-byte accesses for small objects
and bounded eight-byte loops with exact tails for larger objects. It uses only
reserved x16/x17/x30/v31, before x30 captures an indirect target and before scalar
argument copies. It makes no runtime helper call and preserves allocatable GP/FP
values. Arguments passed through Darwin `...` receive their private pointer in
an eight-byte stack slot.

This implements the reference's indirect ARGVAL path. It does not by itself
classify small C aggregates, HFAs/HVAs, grouped register arguments, multi-register
returns, or the dedicated x8 indirect-result pointer. Separate grouped and result
interfaces below provide those ABI roles; compiler classification remains open.

Checks cover malformed construction and illegal uses, distinct/aligned per-use
copy placement, bounded code through i32::MAX bytes (emission only), 74 native
protected-boundary copy sizes, and 672 whole-function size/alignment/frame/GP-FP/
fixed-variadic combinations. The latter retain forty values through repeated
mutating calls, including two copy pointers on the stack, and verify untouched
source bytes. Four linked fixtures exercise aligned dynamic objects and both
result banks for fixed and variadic calls.

## Grouped scalar pieces

`calls/create-grouped(flags, result, parameters, groups, allocator)` describes
arguments that must travel together. `call-groups/Group` contains `first` (a
zero-based ordinal in the flattened scalar list), `count`, and `alignment`.
Records are sorted, disjoint, and cannot cross the fixed/unnamed boundary.
Existing `calls/create` keeps the original scalar prototype bytes unchanged.

Supported groups are two identical U64 or I64 pieces, or one through four
identical f32/f64 members. These are classified ABI pieces, rather than source
record addresses. The frontend must classify and marshal the source aggregate,
including exact-width loads of partial words. Group alignment is a power of two
from the member width through sixteen, and the complete payload must satisfy it.
For an integer pair, use eight- or sixteen-byte alignment. HVA/vector pieces and
padded homogeneous representations are outside this interface's current coverage.

Use the same grouped prototype with `calls/function!` for an incoming function.
PARAM ordinals still index the flattened pieces. The complete prototype retains
all group members even when some PARAM projections are unused or absent.
Outgoing calls and incoming parameters now use one Darwin layout planner.
Groups fit completely in their bank or go completely to the stack and exhaust
that bank. The other bank remains independent. Darwin permits a sixteen-aligned
integer pair to start at an odd-numbered register.

Named floating groups keep tightly packed members in memory with their declared
alignment and payload size. For example, a three-float group can occupy stack
bytes4..15 after a one-byte stack argument at0. An unnamed group uses eight-byte
stack alignment and rounds its whole extent to eight bytes. Its f32 members are
not individually promoted to double; an ordinary unnamed f32 scalar still is.
Call-site descriptors may cover unnamed arguments beyond the fixed type prefix;
those members are checked against actual operands. Function declarations may
only describe their named parameters.

Grouped prototypes retain the upstream flags/result/count/type prefix, followed
by a Coil extension when groups exist: `SGAG`, version1, a zero byte, u16 record
count, then eight-byte records containing u16 first, u8 count, u8 alignment and
four zero reserved bytes. Integers use little-endian order. Empty extensions,
unknown versions, nonzero reserved fields, malformed/truncated records and
incompatible types are rejected. Extended signatures describe Coil's additional
ABI contract; they are not an upstream aggregate-prototype format.

The native tests compare actual C aggregate interfaces in both directions,
including aligned integer pairs, f32/f64 homogeneous groups of every supported
length, register-bank boundaries and omitted incoming projections. C callbacks
use explicit exports and typed by-value pointers to select Coil's C ABI thunks.
Outgoing functions retain forty integer or floating values through the callback.
Named calls use resolved JIT images and linked external C symbols.


## Aggregate result storage

`calls/create-result(flags, parameters, groups, result, allocator)` describes a
classified aggregate result with an explicit storage operand. Its IR return type
is VOID, and fixed parameter ordinal zero must be ADDR. This address is a CALL
operand and a generated function PARAM, rather than an ordinary native argument.
VAR and ARGVAL references cannot stand in for the result address. The caller must
provide writable storage for the complete classified extent and any alignment
required by the source ABI.

`call-results/pieces(type, count)` supports one or two U64/I64 words, or one
through four homogeneous F32/F64 members. The result address consumes no native
argument register or stack slot. Before calling, the emitter saves it in a
private outgoing slot. Immediately after the call it writes the complete return
bank into that storage, before allocation transfers can overwrite those registers.
A generated callee exposes a private fixed-frame buffer as PARAM zero; its body
writes the classified pieces there and RETURN installs x0–x1 or v0–v3 from it.
Every executed return must have initialized the required pieces.

`call-results/indirect()` passes the result address in x8 independently of x0–x7.
The callee writes directly through PARAM zero. No post-call result-bank capture
or return-bank installation is needed. Fixed parameters after ordinal zero use
the normal argument banks and stack placement, including grouped arguments.

Partial integer aggregates need storage for the full coerced register extent.
For example, a three-byte record uses one eight-byte classified word. Source
padding has unspecified contents; compiler marshaling must preserve logical
fields without reading beyond the source object's bounds. The result-storage
contract does not perform source-language aggregate classification.

Aggregate signatures append SGAG version2 to the unchanged scalar prefix. The
sixteen-byte header contains magic at0..3, version at4, result kind at5, little-
endian u16 group count at6..7, result piece type/count at8..9 and six reserved zero
bytes at10..15. Group records retain their eight-byte format. Kind1 is a register
result; kind2 is indirect and requires zero type/count. Kind0 uses the original
scalar encoding or version1 grouped encoding. Unknown kinds, malformed shapes,
invalid result roles, reserved bytes and truncated trailers are rejected.

Focused tests cover 204 native graph variants with real C aggregate interfaces:
integer words, homogeneous floating results, indirect records and partial logical
payloads. They check exact payload bits, live values across nested calls, dynamic
stack storage, over-aligned frames and surrounding output bytes. Thirty linked
AOT objects exercise both directions, including named calls through resolved JIT
images and external C symbols. Twelve additional self-recursive functions run
through JIT and linked AOT with 16/4096-byte alignment, dynamic storage, two return
paths and depths through31. They check per-frame guards after recursive calls and
exact logical field bits. Protected-page checks cover all twelve register-result
shapes, with both ends of source/destination extents abutting inaccessible pages
and complete surrounding-byte comparisons. Vector results and compiler-specific
classification/marshaling remain open.


## Short-vector transport foundation

`types/vector-type(base, count)` constructs the upstream byte encoding: scalar
base in bits0..3 and log2(count)+1 in bits4..6, for power-of-two counts1..64.
`vector?`, `valid?`, `base-type`, `lanes` and `size` validate/decode that geometry;
`size` takes the target pointer width. Void has zero lanes. The existing
`valid-scalar?`, scalar predicates and `scalar-size` retain their behavior.
Representation validity does not imply that an operation or target accepts that
shape. `short-vector?` identifies vector extents of eight or sixteen bytes.

The native transfer layer now accepts sixteen-byte payloads in SIMD registers
or stack slots. Full-width register moves use ORR Vd.16B,Vn.16B,Vn.16B, rather
than scalar FMOV, and memory operations use Q-register loads/stores. Scaled
immediates and materialized large/unaligned addresses share the checked frame
access path. A sixteen-byte GPR or cross-bank transfer is rejected, including
an identity transfer through a GPR. Invalid transfers preserve output bytes.

A sixteen-byte memory-to-memory transfer needs a caller-owned SIMD data scratch,
separate from a GPR address scratch. `parallel-frame!` uses reserved v31 for the
cycle value, v30 for memory data and x16 for addresses. Scalar groups retain
their existing scratch policy. Every simultaneous group has one raw width and
distinct stack identities must describe nonoverlapping storage extents.

Forty-eight native cases exercise register, stack and mixed cycles, fan-out,
large/unaligned offsets and frame bias, comparing complete buffers and preserved
flags. Protected-page checks put both ends of sixteen-byte source/destination
extents against inaccessible regions. Instruction words match LLVM MC reference
output. A separately linked Mach-O fixture verifies a four-way register/stack
cycle through large, unaligned frame slots and preserved flags. This foundation
does not yet enable vector graph operations, allocated
vector values, or vector/HVA signatures; those still report unsupported types.
