# Coil StogIR implementation plan

Status: scalar integer and selected floating AArch64 JIT/shared-image Mach-O AOT work;
upstream compatibility, backend integration, and performance gates remain open.

## Scope and reference

Build a standalone Coil compilation library first, then a Coil compiler backend.
Reference: https://github.com/dstogov/ir at
92171d0a4a36b0acf707f2dea7998de615dd4acd (inspected 2026-10-31).
The neighboring coil-tpde package demonstrates the package/backend separation.
This is a Coil implementation, not an FFI wrapper around the C framework.

Keep the library's license and upstream credit in LICENSE, NOTICE and
docs/PROVENANCE.md, with source links in README. Source/binary distribution and the later
Coil backend vendoring step must carry the applicable notices and license texts.
Audit any additional reused source under its own license before incorporating it;
IR's MIT license does not cover other projects' source.

## Architecture

Follow upstream's single compact Sea-of-Nodes representation: indexed nodes,
explicit control dependencies, floating pure computations, phi nodes, and
separate constant storage. Derive the precise layout and opcode metadata from
ir.h and ir.c before implementing storage. Specify reference validity, variable
arity, growth, ownership, and allocation failure behavior before exposing APIs.
Keep graph construction independent of Coil compiler internals and host runtime.

Preserve upstream's pipeline and track each stage against its source:

| Stage | Reference |
| --- | --- |
| Types, opcodes, storage | ir.h, ir.c |
| Builder and local folding/CSE | ir_builder.h, ir_fold.h |
| Validation and serialization | ir_check.c, ir_save.c, ir_load.c |
| Conditional constant propagation | ir_sccp.c |
| CFG and global code motion | ir_cfg.c, ir_gcm.c |
| Scheduling and selection | ir_emit.c, target .dasc files |
| Register allocation | ir_ra.c; audit fast/simple alternatives |
| Target emission | ir_aarch64.dasc, ir_x86.dasc |

Maintain an explicit port-coverage inventory. Do not silently substitute a
block IR, ad hoc optimization rules, or a different allocator.

## JIT and AOT boundary

Code generation produces sections, symbols, alignment requirements, relocations,
and target/ABI metadata. It must not depend on final memory addresses.
JIT resolves symbols, lays out sections, applies relocations, finalizes executable
memory permissions, synchronizes instruction caches, and owns image lifetime.
AOT writes relocatable objects with the same symbols and relocation semantics.
Calls to external functions and references to data must work through both paths.
Design both paths before committing to an emitter API; no absolute-address-only
shortcut. Audit upstream's object support rather than assuming JIT emission
already provides all AOT requirements.

Start with native macOS AArch64. Add x86-64 and platform object formats through
explicit target/ABI implementations. Reuse neighboring emitter/object code only
after auditing semantics, dependency boundaries, and licensing; do not couple
this library to TPDE's compiler adapter. Linux-specific validation uses the
existing computer.jimmyhmiller.com host only when needed.

## Delivery gates

1. Foundation: package, opcode/type inventory, graph storage, builder, verifier,
   deterministic dump, and graph tests including loops and invalid input.
2. Folding and SCCP: typed semantics, overflow and floating-point behavior,
   executable differential tests against pinned upstream.
3. CFG, motion, scheduling: dominance, loops, effect ordering, phi edges.
4. Selection/allocation/emission: native integer/control/call slice with spills
   and ABI tests. Run identical functions through JIT and linked AOT objects.
5. Complete scalar/vector semantics, floating point, memory, relocations, aggregate
   ABI lowering, and target coverage. Unsupported operations must produce explicit diagnostics.
6. Integrate Coil lowering only after standalone correctness and performance
   gates pass. Keep compiler-specific lowering in an adapter package/module.

Each milestone must report supported operations and remaining gaps. A constant
return demo is an early test, not completion of the library.

## Performance evidence

Measure construction, folding, optimization, scheduling, allocation, emission,
JIT finalization, and object writing separately; also report end-to-end latency.
Record input size, instructions/sec, peak memory, emitted bytes, compiler version,
optimization settings, hardware, warmup and repeated-run distributions.
Use fixed straight-line, branch-heavy, loop, call, memory, and spill-pressure
corpora at increasing sizes. Compare equivalent pipelines with pinned upstream;
compare TPDE for context, accounting for different optimization work. Include
execution time so faster compilation cannot hide unusable generated code.
Set numerical regression budgets after collecting reproducible baselines.

## Current implementation and next step

Implemented in Coil: graph storage, typed constants, local integer folding/CSE,
use lists, CFG, dominance, natural-loop depth, placement, scheduling, phi moves,
live ranges, split-interval allocation, spill frames, AArch64 scalar integer
selection/emission, native JIT mapping and limited Mach-O object writing. Native
tests exercise arithmetic, branches, loops, phi cycles, spills, memory, and
conversions. Indirect calls support scalar integer, bool, char, and address arguments,
Darwin fixed and integer variadic stack arguments, retained interned prototypes,
result locations, live-through spills, and a linked x29/x30 frame record.
Incoming integer scalars include narrow/pointer stack parameters and mixed-class
signature layout even when floating projections are unused. A shared image model
and transactional relocation planner support ABS64, BRANCH26, PAGE21, and
PAGEOFF12; the JIT resolves external branches through veneers. Mach-O consumes
the shared text/data image with local/exported/undefined symbols and explicit
relocations, including signed addends. `compile/image` exposes the owned boundary.
Named FUNC calls, FUNC/SYM addresses, and STR literals now lower through this
image boundary, including self-recursion, address phis, and temporary-buffer
reference rebasing. Additional object features remain open; see IMAGES.md.

Integer binary selection/emission now covers ADD/SUB/MUL/DIV/MOD, MIN/MAX, bitwise logic,
shifts and rotates across all scalar integer widths, including target-width
addresses. Boolean binary computation supports OR/AND/XOR; integer comparisons
cover every scalar integer type. DIV uses SDIV/UDIV; MOD uses a quotient scratch followed by MSUB, preserving both inputs
when the allocated result aliases either input or both literals occupy x16/x17.
ROL negates the count into scratch and uses RORV, including wrapped counts.

DIV/MOD keep upstream's third optional control-guard operand. The checked
`builder/integer-division!` accepts the guard explicitly; the generic integer
binary helper requests no guard. Guard identity participates in CSE, semantic
validation accepts only block starts or GUARD/GUARD_NOT, and scheduling preserves
the dependency. Constant folding handles all scalar integer widths, leaving
zero divisors and signed minimum/-1 operations unfolded as upstream does.
Runtime AArch64 division by zero yields quotient zero, and the remainder
sequence yields the dividend. Signed minimum/-1 yields the minimum bit pattern
and remainder zero. These are current target behaviors, not portable exception
promises; see Arm's [SDIV reference](https://support.arm.com/documentation/ddi0602/2024-12/Base-Instructions/SDIV--Signed-divide-?lang=en).

Native regression matrices cover signedness, 32/64-bit and address widths,
zero/overflow cases, counts at/beyond the width, and all constant/register
operand combinations. Guard/CSE/placement tests and linked Mach-O functions
exercise combined DIV+MOD+ROL graphs. Remaining integer families and upstream
selection/optimization parity remain open.

Scalar unary selection/emission now covers NEG, NOT, signed ABS, BSWAP,
CTPOP, CTLZ, and CTTZ. Type policy is shared by checked construction, folding,
verification, and target validation. Narrow 8/16-bit inputs/results are
normalized locally; 32/64-bit forms use their architectural register width.
Boolean NOT uses a comparison and set, and ABS preserves the minimum signed
bit pattern on overflow. BSWAP requires at least 16 bits; address NOT/BSWAP and
bit counts use target pointer width. Pure unary expressions share a CSE entry.

CTLZ/CTTZ of zero remain undefined, as stated in upstream ir_emit_llvm.c;
constant folding leaves those cases unfolded. CTPOP uses the baseline SIMD
CNT/ADDV sequence with reserved v31, encoding both source and destination
fields. Graph selection currently accepts only GPR-valued computations; register-class
allocation and physical SIMD transfers are now implemented, with v30/v31
excluded from the SIMD mask. Future vector allocation must retain the scratch
reservation or replace it with an allocated temporary. This foundation does not
provide end-to-end floating-point IR support.

Tests cover 248 unary graph variants across scalar widths, signedness,
constants, minimum values, zero and dynamic parameters, plus folding against
an arithmetic oracle and symbol-aware address NOT. Linked AOT tests combine
all applicable unary families for signed 8/16/32/64-bit and unsigned 64-bit
functions, including widening narrow results before further computation.

Narrow binary operands normalize into reserved x16/x17, preserving original
live values and honoring signed division, signed comparisons, and SAR independently
of the declared unsigned/signed type. Narrow results normalize by their type.
Shift counts are masked to width-1; byte/halfword rotations repeat the narrow
pattern in a W register before RORV. This gives folding and execution consistent
width-masked counts. Some upstream narrow target paths differ for out-of-range
counts; see the recorded upstream consistency follow-up rather than assuming
full cross-target parity for those cases. Boolean signed comparisons treat
canonical true/false as positive byte values, correcting an earlier local fold bug.

A 972-variant native matrix checks binary families and all ten comparison
predicates against an arithmetic oracle, including constant/register combinations,
upper-bit contamination, wrapped counts, signed boundaries, address-valued
operations and Boolean logic. Linked narrow combination functions preserve both
original inputs and cover signed/unsigned byte/halfword arithmetic and Boolean LT.
The 24-value call-pressure test now includes i8/i16 values, widening for a call and
storing originals afterward. It exposed a local spill ordering bug: even-position
reloads and odd-position pre-clobber stores must be separate ordered groups, not
one parallel group. The emitter now indexes transfers by exact subposition and
traverses those groups in O(nodes + transfers); other allocator scaling debts remain.

Integer MIN/MAX compare using declared signedness, including BOOL and target-width
addresses. Constant folding preserves the chosen reference and its metadata;
identical inputs fold to that value, and commuted integer extrema share CSE.
The binary/comparison regression matrix now has 1,060 graph variants.

`builder/conditional!` constructs scalar COND from a condition and two matching
value arms. It folds numeric integer/floating conditions (signed zero is false,
NaN is true), preserves selected references, folds identical arms, and uses an
exact three-input CSE key. Its semantic validator accepts scalar metadata;
target lowering currently requires integer conditions/results. Named address
truth remains unresolved during folding because image bindings explicitly permit
address zero; this conservatively omits upstream's named-nonnull simplification.
Both arms are existing SSA values. Conditional side effects use explicit control
nodes.

Integer COND captures flags before materializing its arms into x16/x17. Shared
materialization preserves NZCV and reports emitted bytes consistently for numeric
and symbolic forms. This supports three literal inputs, narrow widths, source/
result aliases and named pointers. An 869-variant conditional matrix covers all
integer condition/result type pairs, constants and aliases. Linked typed
MIN/MAX+COND functions and symbolic conditional images run through AOT; the same
image runs in JIT with zero, one and high-bit external symbol addresses after
its graph has been released. The 24-value call-pressure test also includes
conditional wide/i8/i16 results retained across the call.

The current graph uses two contiguous arrays for signed reference spaces instead
of upstream's single allocation; benchmark and revisit this physical-layout
choice. Node-start and arity metadata currently use a parallel i32 array.

Narrow calls extend register arguments after parallel copies, pack fixed stack
slots at natural widths, and promote unnamed narrow integers for Darwin varargs.
Call/function results include narrow scalars and void; RETURN value typing is
verified before emission.

Next: variadic argument access and remaining floating operation, memory and
conversion selection. Floating scalar ABI is now implemented. Function declarations now preserve omitted
parameter types, and entry scheduling/reservations protect incoming values.
Callee prototypes use upstream-shaped PROTO nodes with interned binary strings,
or 16-bit header metadata for FUNC/FUNC_ADDR constants; semantic verification
checks types, arity, and metadata. Named FUNC/SYM/STR graph construction and
emission use owned image symbols, address slots and literal bytes.
The Darwin backend supports default/explicit Darwin conventions and integer
variadic calls; other conventions and unsupported argument types report errors.
The builder retains ABI metadata even when the target cannot lower it.
Complete additional special constants and object features, and audit missing
upstream semantics and SCCP. Full semantic/dominance verification and irreducible loop
handling remain incomplete. Several allocation, transfer and placement paths
need scaling work. No code-generation performance claims exist yet.

### Checked integer arithmetic in progress

ADD_OV, SUB_OV and MUL_OV now construct typed non-Boolean integer values with
OVERFLOW Boolean projections. Non-overflowing numeric constants fold; overflowing
constants retain their producer. Commutative checked operations and projections
share expression keys, invalidated by graph mutation. A pre-allocation scheduling
pass places each projection beside its producer and validates adjacency before
emission. Projections capture NZCV into ordinary allocated Boolean values.

AArch64 uses ADDS/SUBS for 32/64-bit addition/subtraction, widened products for
32-bit multiplication and high-half comparison for 64-bit multiplication. Narrow
operations compare full intermediate values with their truncated extension.
Unused overflow results avoid flag computation. Focused native coverage currently
passes 270 variants across integer widths, register/literal inputs, two live
checked producers, duplicate projections, a caller-register/NZCV-clobbering call,
and overflow-driven branches with Boolean phi results. Both wrapped values and
captured flags remain live across the clobbering call. Builder, folding,
adjacency validation and assembler encoding checks also pass. Ten generated
Mach-O objects pass 6,300 linked checked-operation cases (14 by 15 input pairs,
three operations, ten types), checking each wrapped value and flag against
wider-integer arithmetic. Twenty-four generated pressure graphs (three checked operations across signed
and unsigned 8/16/32/64-bit types) keep 24 wrapped results and 24 overflow flags
live across a 24-argument call, then verify every stored result/flag and the call
result. Fifteen input edge cases pass in every graph. This exercises projection
capture, splitting, spill slots, reloads and later Boolean selection together.

### Scalar conversion policy and bitcasts

`stogir.conversion` now shares SEXT/ZEXT/TRUNC/BITCAST type/width policy between
construction, constant folding, semantic verification and AArch64 selection.
The builder exposes `conversion!`; numeric folds mask source/destination widths,
bitcasts preserve floating payload bits, and expression reuse includes source,
result type and target pointer size. Mutation invalidates the cache. Identity
bitcasts preserve the original reference, including named address annotations.

SEXT uses the source storage width regardless of signedness; canonical Boolean
true therefore extends to +1. Boolean destinations first retain the low storage
byte and then canonicalize nonzero to 1 in both folding and native lowering.
This agrees with upstream folding while avoiding a source discrepancy in its
AArch64 raw-byte conversion emission. LLVM i1 casts require explicit handling
in the eventual Coil frontend, as the current TPDE frontend already does.

AArch64 now selects all integer/address conversions and same-width integer
bitcasts, retaining relocation references when reinterpreting a named address.
Each conversion emits into a temporary owned buffer so failure does not partially
append bytes or references. Floating/integer constant bitcasts fold as exact bits;
raw floating constants can also materialize into integer results. Live floating
sources/destinations still require floating conversion selection; scalar ABI,
register-class allocation and physical transfers are now implemented.

Focused validation passes all 165 valid integer conversion/type combinations
with edge inputs, four raw floating constant bitcasts, construction/folding/CSE
and invalid-input cases, 32-bit pointer policy, named function/string bitcasts,
zero/full-width image resolutions after graph release, and a linked symbolic
pointer-to-integer consumer. All 117 standalone tests and 20 linked AOT consumers pass locally with debug
checks. The project pad records the validation scope and remaining work.


### Register classes and scalar SIMD transfers

Allocation now supports per-value admissible register masks, preserves them
through splitting/eviction and checks fixed assignments and split consistency.
Register ID validation precedes pressure indexing. Mixed-class tests allocate
three values per class on two registers per class, forcing spills without using
spare registers from the other class; highest-bit register 63 is also covered.
AArch64 defines separate GPR/SIMD numbering, reserves scratch registers and
excludes callee-saved SIMD registers. GPR-only functions retain 16-register scans.

Scalar physical transfers now handle SIMD moves, loads/stores and raw GPR/SIMD
bit transfers. Parallel copies encode stack locations beyond all 64 physical
register IDs. LLVM MC goldens verify instruction words; native tests preserve
NaN/signed-zero payloads through separate and mixed GPR/SIMD/stack cycles at both
32 and 64 bits, including direct SIMD-stack cycles and error atomicity.
Live floating graph PARAM/RETURN/call ABI and exact-bit argument/return constants
are connected in the following stage. Floating operations, memory and conversion
selection remain next work, with requirements tracked in the project pad.

After the register-class/transfer changes, all 119 standalone tests and 20 linked
AOT consumers pass locally with Coil debug checks. This verifies the existing
integer backend and the new physical foundation; it preceded the floating ABI
changes below.


### Live floating scalar ABI

Live f32/f64 PARAM and RETURN now use SIMD constraints, incoming reservations,
register/stack capture and exact-bit constants. Calls classify every argument
with independent GPR/FPR banks, share that plan between outgoing frame sizing and
emission, resolve register copies before constants and preserve both caller-saved
classes. Integer and FP result-bank exceptions are distinct. Darwin variadic
f32 arguments convert to double in reserved v30 before their eight-byte stores.

Focused tests pass 30 incoming/return variants, including stack arguments above
a non-leaf frame and PARAM projections constructed after the call, exact NaN and
signed-zero bits; five mixed-call/result/live-through variants with ten integer
and ten floating arguments; JIT/linked variadic promotion via snprintf; and linked
mixed-call and non-leaf FP-stack consumers. All 122 standalone tests and 23 linked AOT consumers pass locally with debug
checks; the final call-before-PARAM strengthening passed a separate native rerun
and its regenerated objects passed linked execution. Floating arithmetic/comparison/memory/conversion and complete phi/constant
selection are still unfinished, alongside the remaining full-library and compiler
integration/benchmark gates.


### Floating operations, memory and exact-bit flow

`stogir.floating` supplies typed construction, constant evaluation, ordered CSE,
guard validation and shared policy. Native f32/f64 selection now includes
ADD/SUB/MUL/DIV, NEG/ABS, all twelve predicates and MIN/MAX. Comparisons distinguish
ordered relations from unordered-or relations using the upstream condition map.
No reassociation or fast-math identities are introduced. DIV retains its optional
guard as a dependency, as with integer division.

MIN/MAX consistently use ordered compare-and-select, including constant folding:
equality preserves the left signed zero; unordered comparison selects the right
operand's raw payload. This matches upstream folding and intentionally avoids the
FMINNM/FMAXNM source discrepancy in upstream's AArch64 emitter, recorded as a
qualified follow-up in the project pad. Operand order is retained in CSE.

A shared typed operand helper materializes exact-bit FP constants in reserved
SIMD scratches. Floating loads/stores (including volatile forms), live same-width
GPR/SIMD bitcasts and FP phi literals use that helper. Memory emission uses an
owned temporary buffer so errors cannot partially append bytes/references.
Phi copies precede typed literal installation; spill literals use reserved SIMD
temporaries with eight-byte scalar spill slots.

Focused native evidence: 240 arithmetic/predicate/extrema variants (both widths,
register/literal combinations, aliasing and on-build folding); 48 memory/bitcast
configurations with byte canaries and unaligned/literal addresses; eight FP phi
configurations; and two 24-value FP call-pressure graphs that exceed the 22-register
SIMD pool and preserve values across a 24-argument call. Predicate/extrema tests
use an independent IEEE bit-classification/order oracle; arithmetic checks permit
any NaN payload while requiring exact non-NaN results. Unary operations, selected
extrema, memory, bitcasts and phi values preserve the expected raw bits.

Linked AOT tests cover 7,840 arithmetic/predicate/extrema results plus exact-bit
unaligned floating memory/bitcasts and signaling-NaN/signed-zero phi constants.
LLVM MC goldens match the scalar arithmetic, unary, compare and select encodings.
Numeric floating conversions, remaining truth/control selection, further full
library semantics/optimization, Coil backend integration and equivalent LLVM/TPDE
compile/runtime measurements remain open. Full regression results are tracked
in the project pad.


After the floating operation/memory/bitcast/phi changes, all 128 standalone tests
and 26 linked AOT consumers pass locally with Coil debug checks. This is not full
library/backend completion or a compile/runtime performance claim.


### Numeric conversions and complete scalar truth/selection

INT2FP/FP2INT/FP2FP now share the scalar conversion builder, policy, CSE and
validator. FP-to-int folding exactly decodes IEEE bits, truncates the significand
with integer shifts, and checks the destination range before returning a constant.
It does not invoke host FP-to-int casts. Non-finite and unrepresentable results
remain native instructions. Integer-to-f32 folding converts directly at the
requested precision; midpoint tests catch double-rounding regressions. FP2FP NaNs
remain unfolded when precision changes, while same-type conversions preserve bits.
Native selection uses SCVTF/UCVTF, FCVTZS/FCVTZU and FCVT, with local source
normalization and canonical byte-oriented Boolean destinations.

One typed truth emitter now serves IF and COND. It fixes IF's former low-word-only
comparison of 64-bit values and adds floating nonzero tests against zero. Both
signed zeros are false and NaNs true. COND supports every scalar condition/result
combination, including mixed GPR/SIMD banks and three literal operands, preserving
NZCV through arm materialization.

Focused evidence passes 273 boundary/folding cases, 144 native numeric-conversion
variants, 1,066 truth/selection variants, and linked consumers for both. New native
and linked loops cover FP arithmetic state and simultaneous FP phi swaps with
signaling-NaN payloads preserved. Full regression results are tracked in the pad;
further library/control/intrinsic semantics, allocation/scaling work, compiler
integration and equivalent LLVM/TPDE benchmarking remain open.


After numeric conversion, scalar truth/selection and floating-loop changes, all
132 standalone tests and 29 linked AOT consumers pass locally with debug checks.
The standalone run resumed after updating two obsolete floating-COND rejection
assertions. The next concrete gate is local/dynamic stack storage, with stable
frame anchoring and outgoing-call areas handled correctly before enabling it.

The first storage prerequisite now separates local-object identities from split
value spill identities in the generic frame layout. Requests share one checked
offset space, but independent ownership maps prevent an object's storage from
aliasing a spill of its address. Repeated requests must agree on size/alignment;
overflow leaves ownership and slot state unchanged.

AArch64 fixed-frame helpers now materialize large offsets and use extended
register ADD/SUB when an immediate cannot encode the address or adjustment.
Function entry/return stack adjustments use these helpers. Native tests exercise
16-byte, 4 KB, 8.8 KB and 64 KB frames and preserved condition flags. This does
not yet enable VAR/VADDR or dynamic allocation; remaining memory-offset limits,
local instruction lowering and stable dynamic-frame anchoring remain open.

After these prerequisites, all 133 standalone tests and 29 linked AOT consumers
pass locally with debug checks; linked consumers use regenerated objects.

Scalar local instructions are now connected through shape/extent validation,
graph dependencies, register liveness, constraints, frame allocation and typed
AArch64 emission. VAR remains a storage object; VADDR produces its separately
allocated pointer value. VLOAD/VSTORE and volatile variants support all scalar
types and mixed views within the declared extent. The target rejects alignment
above sixteen until aligned frame anchoring exists.

Focused tests cover 832 native variants, local state in integer/floating loops,
24 addresses live through a mutating call with forced spills, and an 8.8 KB
frame with 1,100 initialized objects. Seven objects link into the new AOT local
consumer. Full regression results are tracked in the project pad. Dynamic stack
allocation, FRAME_ADDR, over-aligned frames, remaining library semantics and
optimizations, compiler integration and LLVM/TPDE comparisons remain open.

After scalar local lowering, all 137 standalone tests and all 30 linked AOT
consumers pass locally with debug checks. The passing standalone set matches
every top-level standalone test file, and linked consumers use regenerated
objects. Current evidence and remaining work are indexed in the project pad.

Fixed storage now has an explicit SP/x29 base context threaded through transfers,
incoming arguments, local accesses, phi-edge emission and call operand capture.
FRAME_ADDR is validated and selected; its target policy establishes a real frame
record even in leaf functions. Anchored returns restore fixed SP from x29 before
loading saved registers. Ordinary functions keep the SP-based path.

Focused execution covers a leaf's prior-frame link/saved LR, 32/64-bit
GPR/SIMD/memory cycles after deliberately moving SP, and ordinary/anchored
variants of incoming stack arguments, local call pressure, large local frames,
FP call pressure and FP arithmetic/phi-swap loops. Full regression is tracked in
the pad. ALLOCA/AFREE and the live dynamic-object/outgoing-call layout remain
unimplemented; frame contexts are their stable-base prerequisite.

After anchored-frame support, all 139 standalone tests and 30 linked AOT
consumers pass locally with debug checks. Linked consumers use regenerated
objects. The moved-SP cycle test additionally passes anchor biases through
8.8 KB, exercising large-offset SP restoration as well as ordinary immediates.

ALLOCA/AFREE now lower constant and dynamic counts with identical sixteen-byte
rounding, declared-width normalization and count-domain validation. Dynamic
functions select the anchored fixed-frame path. A function-wide outgoing prefix
stays below live objects: allocation subtracts its rounded size and returns
SP+outgoing-size. This keeps outgoing stack arguments separate from dynamic data.
Every return restores fixed SP from x29, including paths that retain allocations.

Focused execution covers 1,000 nested size/type/alignment variants, isolated
invalid-count trap checks, fixed guards plus 24 dynamic addresses through a
mutating call with forced spills, FP call pressure with a count retained until
AFREE, incoming stack arguments, integer/FP dynamic-object loops and distinct
return depths. Four new objects link through the dynamic-storage AOT consumer.
The earlier local-address pressure test's unused FRAME_ADDR dependency has been
corrected; evidence and full regression results are tracked in the project pad.
Over-aligned frames, remaining library/control/intrinsic/aggregate/vector/atomic
semantics and optimization/scaling, compiler integration and equivalent
LLVM/TPDE measurements remain unfinished.

After dynamic-stack lowering, all 144 standalone tests and 31 linked AOT
consumers pass locally with debug checks; linked consumers use regenerated
objects. Subsequent removal of repeated per-file license headers changed
comments only. Licensing and upstream attribution remain centralized.

Large scalar frame accesses now fall back to explicit address materialization.
This reaches spill transfers, incoming arguments, outgoing argument stores and
saved frame records. Parallel frame copies use reserved v31 for their cycle
value, leaving x16/x17 for addresses/data; dense stack IDs preserve i64 offsets.
Focused checks execute memory-range boundaries and distant mixed copy cycles,
whole functions with 4,200 fixed objects and forced GP/FP spills, and 4,105-argument
variadic calls with frame records/outgoing slots beyond 32 KB. Linked large-call
objects execute too. Offsets beyond i32 have emission-only checks.

This work also fixed a constructor restriction that confused the 255 fixed
prototype-parameter limit with total variadic arguments. The upstream prototype
format is unchanged; CALL's sixteen-bit input count admits 65,533 actual arguments.
Boundary tests check acceptance/rejection and no graph mutation on overflow.
Full regression results and remaining delivery gates are indexed in the pad.

After large-memory access and variadic-count fixes, all 147 standalone tests
and 32 linked AOT consumers pass locally with debug checks. The standalone
passing set exactly matches the test files; linked consumers use regenerated
objects. Compiler integration and performance comparisons remain unfinished.

Over-aligned frames now select the maximum requested alignment, realign actual
SP and preserve original entry SP in the frame record. Incoming stack parameters
use the saved pointer; return restores it exactly. Outgoing prefixes and every
ALLOCA/AFREE count round to that same function alignment, keeping dynamic objects
aligned and separated from outgoing arguments. Ordinary sixteen-byte frames keep
their existing layout and constant-displacement incoming path.

Focused checks cover 1,664 scalar local variants through 4 KB, 2,640 nested stack
variants through 8 KB, alignment-dependent count overflow, large aligned GP/FP
pressure and outgoing-area expansion. An independent caller sweeps all 278
sixteen-aligned SP residues modulo 32/64/256/4096 and verifies incoming mixed-width
arguments, addresses, calls/free and exact restoration. Linked aligned fixtures
execute too. Full regression and commits are tracked in the project pad.

All 148 standalone tests and 33 linked AOT consumers pass locally with debug
checks. The standalone file set is fully covered. A focused rerun also passes
the 4,105-argument dynamic-call fixture after raising its alignment to 64 bytes,
exercising saved entry SP and frame-record accesses beyond 32 KB. Its linked
consumer passes too. Alignment-mask encoding landed separately as cc458b3.

### Dynamic stack scopes

BLOCK_BEGIN/BLOCK_END now save and restore raw SP using checked `stack-save!`
and `stack-restore!` builders. These operations select an anchored frame even
without ALLOCA or calls. Snapshots include the outgoing argument prefix and
restore the entire scope without reconstructing individual allocation counts.
Their ADDR values participate in normal allocation and fixed-frame spill/reload;
fixed locals and frame records remain anchored through every restoration.
As with the reference IR, callers must restore a live snapshot from the same
function invocation and stop using objects released by that restore.

Native coverage includes 24 nested snapshots live through a ten-argument call,
reverse restoration and pointer equality after every restore, fixed-local guards,
16-byte/4 KB frames, variable allocation counts and save/restore-only leaf code.
The same nested-scope functions are emitted as objects for a linked Coil consumer.
Validation results and the commit checkpoint are recorded in the project pad.

The stack-scope checkpoint passes all 149 standalone tests and all 34 linked AOT
consumers locally with `--debug-checks`, using objects regenerated by that run.
Formatting checks and `git diff --check` pass. All 265 implementation/test files
remain Coil source. Switch lowering is the next identified control-flow gap for
Coil sum matching; compiler integration and comparative benchmarks remain open.

### Integer switch control flow

Checked SWITCH, CASE_VAL, CASE_RANGE and CASE_DEFAULT construction now supports
all eleven integer/address scalar types. Individual validation checks shape,
control, exact endpoint types and inclusive signed/unsigned range order. Complete
dispatch validation requires one default, disjoint ranges and only case control
successors. Cases are ordered with heapsort; signed order uses a sign-bit flip
rather than overflowing subtraction. Graphs without switches do not allocate an
additional dispatch use index.

AArch64 lowering emits balanced comparisons followed by per-case edge-transfer
stubs. The selector stays in x16 until dispatch completes; x17 holds constants.
Existing ordinary/phi transfers reconcile GP/SIMD/spill values at case entries,
merges and loop backedges. A projection omitted from observable roots produces
a diagnostic. The API and remaining dispatch limits are in docs/CONTROL.md.

Focused native and linked checks cover narrow domains, full-width limits,
signed cross-zero ranges, constant/default-only selectors, malformed and
intersecting cases, merged values and integer/FP loops. Pressure fixtures retain
forty pinned memory values across dispatch, use 257 GP or 40 FP cases with calls,
and preserve aligned fixed/dynamic guards. Dense jump tables, long-branch
relaxation, dispatch measurements, compiler integration and the complete
LLVM/TPDE comparison remain open. Full regression is recorded in the project pad.

The switch checkpoint passes all 153 standalone tests and all 36 linked AOT
consumers locally with `--debug-checks`, using fixtures regenerated by the full
standalone run. Formatting checks and `git diff --check` pass. All 273
implementation/test files remain Coil source. Dense jump tables are the next
dispatch task before strategy measurements; compiler integration and whole-backend
LLVM/TPDE runtime/compile-time benchmarks remain required.

### Dense switch jump tables

Dense singleton cases now use the pinned upstream `count>2` and `span<count*8`
selection rule. The target subtracts the normalized minimum, bounds-checks with
one unsigned comparison, and dispatches through ADR/indexed LDRSW/ADD/BR. Holes
use the default edge stub; sparse/range cases keep balanced comparisons. Table
entries are signed 32-bit offsets from their own base, so JIT movement and AOT
linking require no absolute target relocation per entry. All targets still pass
through the existing case-specific edge reconciliation.

Checked ADR, indexed signed-word load and indirect branch encoders match LLVM MC
and landed independently as 4d423fa. Relative-entry fixups validate the complete
patch set before mutation. Native checks include negative/backward entries,
tables near full-width extrema, signed cross-zero intervals, holes, two tables in
one function and simultaneous independently relocated shared-image mappings.
Existing GP/SIMD pressure/call fixtures now take the table path.

Shared code/image data-in-code metadata is validated and rebased through buffer
composition. Mach-O emits LC_DATA_IN_CODE/JUMP_TABLE32, splitting ranges beyond
the u16 length limit. A reference LLVM MC object and a linker warning exposed an
initial file-offset error in the writer: MH_OBJECT entries need section VM
offsets. This was corrected and the focused linked checks now run without those
warnings. Repeat serialization and metadata split validation pass. Full regression
and the final checkpoint are recorded in the project pad. Strategy measurement,
long-branch relaxation, remaining library semantics/optimization/scaling, compiler
integration and LLVM/TPDE comparisons remain open.

The dense-table regression passes all 155 standalone files and all 37 linked AOT
consumers with debug checks and regenerated objects; the linked log has no
warnings. The original-image metadata guard landed during the standalone run,
so jit-image, text-data and jit-switch-tables were also rerun afterward; later
full-run cases used the final source. Formatting and git diff checks pass. All
277 implementation/test files are Coil. UNREACHABLE/TRAP control lowering is a
remaining compiler-facing gap, including defaults for exhaustive sum matching.

### Trap and terminal paths

TRAP and UNREACHABLE now have checked void/control construction and AArch64
emission. The fixed-slot audit found one metadata error: UNREACHABLE's reserved
second word had caused its third terminal-chain slot to be omitted. This is
corrected in d510954; the audit found no other fixed-slot mismatches among the
matching pinned scalar opcodes. Shape validation preserves the reserved zero,
and complete validation checks START heads and terminal targets, permitting
forward links while rejecting cycles with a linear color walk. Zero-only chains
allocate no color array. START or an explicit exit head can retain linked exits.

TRAP emits BRK #0 with a normal control successor. UNREACHABLE emits BRK #0 plus
a branch back to it, ensuring a resumed breakpoint cannot fall through into a
neighboring block. Returning paths keep normal frame restoration. The explicit
UNREACHABLE trap policy is documented against the reference's skipped node in
docs/CONTROL.md. No register value is assigned to either void operation.

Focused native and linked checks cover safe returns and isolated SIGTRAP paths,
IF, dense and sparse exhaustive-match defaults, functions with no RETURN node,
ordinary/aligned dynamic frames, explicit exit roots and START-list roots.
Malformed types, ended controls, reserved words, heads and cyclic chains are
rejected. Full regression and commits are recorded in the project pad. Compiler
integration, remaining library semantics/optimization/scaling and the full
LLVM/TPDE compile-time/runtime comparison remain required.

The terminal-control checkpoint passes all 157 standalone files and all 38 linked
AOT consumers with debug checks and regenerated objects. The final START-head
validation refinement and focused terminal/native reruns landed during the
standalone run; subsequent full-run terminal fixtures used the final source.
The linked log has no warnings. Formatting and git diff checks pass. All 281
implementation/test files remain Coil. Module-image composition and compiler bulk
memory/aggregate operations remain concrete integration requirements.

### Module image composition

`stogir.link/compose` now combines independently compiled images into an owned
module with per-input section bases and stable old-to-new symbol ID maps. Public
declarations resolve against a single definition; private identities are renamed
and isolated. Public names are reserved before private label generation. Input
contents, metadata and relocation records are validated without trusting derived
name caches. Duplicate definitions and malformed inputs fail without mutation of
sources, and partial output is released.

Text/data bytes, symbol locations, relocation locations/targets and text-data
ranges are rebased while addends and internal relative code remain unchanged.
Composition preserves the current image contract of four-byte instruction text
and eight-byte data bases; wider global-data alignment remains an image-format
requirement. Batch composition avoids repeated whole-prefix copies.

Focused checks cover 64 inputs with 1,024 private symbols, repeated declarations,
private/public spelling collisions, malformed symbols/relocations/ranges,
zero-sized conflicting definitions and immutable sources. Independently compiled
mutually recursive functions, shared writable data, a relocated function pointer
and a dense switch compose twice and execute after every original allocation is
released. Text/data prefixes exceed 4 KB/8 KB to exercise page rebasing. A second
JIT mapping proves writable-data isolation. The same module executes as linked
Mach-O; full regression and commit checkpoints are recorded in the project pad.

The module checkpoint passes all 160 standalone files and 39 linked AOT consumers
with debug checks and regenerated objects; the linked log has no warnings. An
exact source/pass-set comparison confirms every standalone file ran once. The
new execution producer is named module-execution.coil to avoid the reserved
*-link.coil consumer convention. Formatting and git diff checks pass. All 286
implementation/test files are Coil. Stronger global-image alignment, compiler
memory/aggregate/atomic/wide semantics, optimization/scaling, backend integration
and LLVM/TPDE runtime/compile-time comparisons remain required.

### Global image alignment

Shared images now retain text/data alignment requirements with four/eight-byte
minimum defaults. Requirements only increase. `image/data-space!` lays out zeroed
objects and padding with checked arithmetic; composition aligns each contribution
and preserves requirement maxima. Pure alignment/JIT planning landed separately
as 48f0902, including overflow and data-only layout checks.

The JIT reserves enough address space for alignment above an OS page, tracks its
original mmap allocation separately from the aligned usable image, and releases
the whole reservation. Prefix/gap/suffix pages remain inaccessible. Only actual
text pages transition RW to RX; data stays RW/NX. The loader supports data-only
images, reserves actual external-branch veneer space, and uses the aligned data
base for relocations. Execution checks cover ten code/data requirement pairs,
globals through 1 MB, above-page code alignment, composition, writable globals,
page-relative data templates and isolated protection faults. Active/reserved-page
probes verify complete release; an initial residency-based probe was replaced
because residency is not a reliable mapping-existence check on this host.

Mach-O retains alignment exponents and aligned data VM/symbol layout, matching
LLVM MC reference objects. AOT checks exercise 4 KB and 16 KB globals/functions.
Apple's linker reduced a 64 KB request to its 16 KB segment maximum, including
with a segment-page-size override; an occasional aligned runtime address did not
prove the requested guarantee. The Darwin arm64 writer now rejects requirements
above 16 KB explicitly. JIT alignment is not restricted to that AOT limit. This
platform boundary is documented rather than silently clamped.

Malformed requirements, monotonicity, padding, reservation overflow and target
limit diagnostics have focused checks. Full regression and commits are recorded
in the project pad. Compiler bulk-memory/aggregate/atomic/wide semantics, full
optimization/scaling, backend integration and LLVM/TPDE comparisons remain open.

The aligned-image checkpoint passes all 163 standalone files and all 40 linked
AOT consumers with debug checks and regenerated objects. Exact source/pass-set
comparison confirms full standalone coverage without duplicates. The linked log
has no warnings. Formatting and git diff checks pass. All 292 implementation/test
files remain Coil. The pure planning checkpoint is 48f0902; the shared image,
loader, composition and target-writer changes form the next checkpoint.
