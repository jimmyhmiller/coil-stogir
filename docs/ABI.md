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
