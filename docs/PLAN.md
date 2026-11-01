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

### Native bulk memory construction

`stogir.bulk` builds copy, overlap-safe move and zero operations using existing
scalar LOAD/STORE and control nodes. Runtime byte counts are U64 references;
`*-bytes!` wrappers accept nonnegative fixed sizes. Addresses must be ADDR values
and control must be an open control chain. Callers supply valid accessible ranges;
copy requires disjoint ranges or identical pointers. Zero bytes performs no access.

Sizes through 64 bytes use exact 8/4/2/1-byte chunks. Small moves capture all reads
before writing. Larger or dynamic sizes use bounded graphs with eight-byte loops
and exact byte tails; moves select forward/backward traversal by unsigned address
order. No libc bulk routine or additional opcode is required. The inline limit is
a code-size policy pending measurement, not a performance result.

Focused checks cover rejected inputs without graph mutation, no-op construction,
bounded dynamic graphs and explicitly unsigned predicates. Native fixed/dynamic
checks compare complete buffers across size, alignment and overlap boundaries.
Protected-page tests exercise exact reads/writes at both ends of accessible
regions, including zero bytes and sizes through 65,537 bytes. Linked AOT checks
execute seven basic bulk fixtures and two dynamic pressure fixtures. The API and
memory contracts are documented in [MEMORY.md](MEMORY.md).

Bulk-memory pressure testing exposed a general block-entry transfer defect:
contiguous split moves at a block's first use position were replayed after CFG
edge copies had already established the entry locations. The preceding block in
layout order need not be an actual predecessor, so that replay could overwrite
live values with another path's register contents. Emission now leaves those
entry transitions to edge reconciliation and retains ordered use/definition
transfers inside blocks. The regression retains forty pinned integer values
through bulk loops, two calls that overwrite all allocatable GPRs, dynamic stack
storage, both move directions and 16-byte/4 KB frame alignment. All sixteen
fixed/dynamic graph variants pass. Focused phi, floating-loop, switch-pressure
and stack-scope checks also pass. This fix is committed as a7b69b0.
Bulk counts and address comparisons now explicitly use ULT/UGT, independent of
operand type, with construction coverage in 29f13ea.


The bulk-memory verification checkpoint passes all 166 standalone checks and all
41 linked AOT consumers locally with debug checks and regenerated objects. Exact
source/pass-set comparisons confirm coverage without duplicates; the linked log
has no warnings. The unsigned-predicate correction and final fixture additions
landed during the standalone run, so final focused construction, native protected
boundary/byte comparisons and call/spill/frame tests were rerun after those
changes, followed by the complete linked run. Formatting and git diff checks pass.
All 297 implementation/test files are Coil. Library optimization/scaling and
remaining semantics, actual Coil backend integration and equivalent LLVM/TPDE
runtime and compile-time measurements remain open.

### ARGVAL indirect aggregate arguments

The reference's AArch64 ARGVAL is an indirect private-copy argument: metadata
contains an address, byte size and alignment, and the consuming CALL receives a
pointer to a fresh copy. It does not classify arbitrary small aggregates or
aggregate results. The checked builder and CALL-only use validation now preserve
that model. Each argument occurrence gets a distinct aligned buffer, even when
one ARGVAL node is reused. Repeated calls refresh their copies. Incoming pointers
continue to use ordinary ADDR parameters.

Private buffers follow scalar stack arguments in the outgoing area; required
alignment raises actual frame alignment, including with dynamic stack objects.
Native exact-width copies use reserved x16/x17/x30/v31 before capturing an
indirect callee and installing arguments. This avoids hidden memcpy calls and
keeps code size bounded for large metadata sizes. Zero-sized arguments reserve
separate aligned bytes and perform no source access. See [ABI.md](ABI.md).

Committed helper checkpoint dc7258f passes 74 protected-boundary copy sizes.
ARGVAL checkpoint fa743fd passes construction/layout/invalid-use checks, emission
through i32::MAX sizes without unrolling, 672 whole-function fixed/variadic,
GP/FP-pressure, frame and alignment combinations, and four linked AOT fixtures.
The whole-function cases retain forty values through two mutating calls, pass
ten separate private copies (two via stack), check preceding writes and original
source preservation, and include null source pointers for zero sizes.

The full standalone regression passes all 169 checks with exact source coverage.
All 42 linked AOT consumers pass after fixture regeneration, with exact consumer
coverage and no warnings. The final
zero-size null-source check was rerun after its addition during the standalone
run; all other implementation behavior remained stable. The source inventory is
303 Coil implementation/test files. Small aggregate grouping, HFA/HVA support,
multi-register and dedicated-x8 results remain aggregate ABI requirements, along
with the remaining semantics, optimization/scaling, actual compiler adapter and
LLVM/TPDE runtime/compile-time benchmarks.

### Grouped argument ABI

Grouped signatures now preserve scalar pieces that belong to one ABI argument.
`calls/create-grouped` carries sorted ordinal/count/alignment records for integer
pairs and homogeneous f32/f64 groups. Ordinary scalar prototypes retain their
exact upstream-shaped encoding; grouped prototypes append the documented SGAG
version1 extension. Named and actual unnamed types, group boundaries and record
structure are checked. Incoming signatures retain complete groups even when
PARAM projections are absent. Both directions now use one Darwin placement
planner, with independent banks, all-or-stack group assignment, odd-register
aligned pairs and group-aware variadic packing. See [ABI.md](ABI.md).

The planner/metadata foundation is committed as 9b309f4 and full integration as
741a625. Review found that a corrupted owned Prototype could serialize as a
valid but different signature after its fixed-count byte wrapped. The concrete
256-byte counterexample is covered, and 8708d3c checks the owned model before
interning as well as validating serialized metadata.

Native checks exercise 56 actual C aggregate interfaces and 165 generated graphs
with five seeds each: complete/omitted incoming projections, indirect calls and
selected named calls through resolved JIT images. Outgoing functions retain forty
GP/FP values across C ABI thunks. Eighteen object fixtures exercise aligned integer
pairs, f32/f64 groups, bank exhaustion, omitted pieces, variadic aggregate packing
and both outgoing call forms. LLVM assembly emitted from Coil probes provides an
independent Darwin stack-layout reference. All implementation/test sources remain
Coil, with normative attribution centralized in PROVENANCE.md.

The initial complete standalone run passed 173 checks. A complete repeat on the
final owned-prototype validation source also passes all 173 checks, with exact
source/pass-set equality and no duplicate runs. All 43 linked AOT consumers pass
after fixture regeneration, with exact consumer coverage and no warnings.
Formatting and git diff checks pass. All 310 implementation/test files are Coil.
Validation used installed Coil d2a49bf21376; ABI assembly probes used Homebrew
LLVM 23.1.4 on this arm64 Mac.
Remaining aggregate work includes multi-register/x8 results, HVA/wide support and
compiler-specific classification/marshaling. Full optimizer/verifier/scaling,
other missing semantics, the compiler adapter and LLVM/TPDE compile-time/runtime
comparisons remain open. These checks do not establish a performance result.


### Aggregate result ABI

Result signatures carry an explicit ADDR storage role at fixed ordinal zero and
use VOID IR calls/returns. SGAG version2 records either a classified register
bank or an indirect x8 result. Scalar and version1 grouped encodings remain
unchanged. Metadata foundation e895d64 checks result shapes and malformed bytes;
71ec270 wires both directions through shared placement, allocation and emission.

Register-result callers save the destination before argument installation and
capture the physical bank immediately after the call. Generated callees expose
a private fixed-frame buffer and install the return bank before their epilogue.
Indirect results use x8 independently of the normal argument banks. Result-place
operands reject VAR and ARGVAL wrappers. Private result buffers remain separate
from user locals and allocator spill identities.

Focused checks pass 192 native graph variants over sixteen C result profiles,
three calling modes, dynamic stack storage and 16/4096-byte frame alignment.
Eleven bit patterns cover signed zero, infinities and NaN payloads. Forty retained
values exercise GP/FP pressure across nested calls. Eighteen linked AOT objects
check outgoing, incoming and forwarding calls. Contract tests check malformed
roles and x8 independence. See ABI.md for the storage and encoding contract.

Named and recursive aggregate-result execution, protected result boundaries,
HVA/wide support and compiler classification/marshaling remain work. The full
regression checkpoint is tracked in the project pad. Optimizer/scaling work,
remaining semantics, actual compiler backend integration and equivalent LLVM/TPDE
compile-time/runtime measurements remain open; no performance conclusion follows
from these correctness checks.


The aggregate-result checkpoint passes all 176 standalone checks and all 44
linked AOT consumers locally with debug checks and regenerated fixtures. Exact
source/pass-set equality confirms complete coverage without duplicate runs;
linked output contains no warnings. Formatting and git diff checks pass. All 316
implementation/test source files remain Coil. Validation used installed Coil
d2a49bf21376 on this arm64 Mac. These counts include the result metadata, contract,
native matrix and linked consumer tests; remaining gates above remain open.


### Named, recursive and protected aggregate results

Checkpoint 3663bfc adds twelve named-call graphs to the result matrix (204 total)
and twelve linked fixtures (thirty total). Named outgoing and forwarding calls
use resolved JIT images and real external C ABI symbols, including register,
partial-word and x8 indirect results under pressure and aligned dynamic frames.

Checkpoint 8dc30cd adds twelve self-recursive aggregate functions: six result
profiles with 16/4096-byte frame alignment. Seven depths through31 and seven bit
patterns cover 588 calls in each of JIT and linked AOT. Both return paths execute;
recursive calls retain the parent result place, depth, local guard and dynamic
object. Parent frames check their guards and modify the returned first field.
Each function's self-reference binds to its sole defined image entry.

Checkpoint 0572960 tests all twelve supported register-result shapes against
protected pages. The native wrapper loads the complete return bank from one
region and captures it into another; start/end placements cover four boundary
pairs per shape. Complete source and destination comparisons catch changes to
surrounding accessible bytes, and fault-isolated children diagnose overreads or
overwrites across either protected boundary. The wrapper preserves host x29/SP.
No library implementation change was needed for these checks.

These checks close the named/recursive and exact register-result access gates
listed at the previous checkpoint. Remaining aggregate work is HVA/wide support
and source-language classification/marshaling in the adapter. Other semantics,
optimization/scaling, backend integration and runtime/compile-time comparisons
remain open. Licensing and source attribution continue to be centralized.


The extended result-verification checkpoint passes all 178 standalone checks
and 45 linked AOT consumers with debug checks and freshly regenerated objects.
Exact source/pass-set equality verifies complete coverage without duplicate runs;
linked output has no warnings. Formatting and git diff checks pass. All 319
implementation/test files remain Coil. The library implementation is unchanged
from 71ec270; these additions expand execution coverage and preserve the remaining
backend and benchmark gates. Logs and commits are indexed in the project pad.


### Short-vector type and transport foundation

Checkpoint da7b1f5 adds checked upstream vector geometry while preserving scalar
identifiers and APIs. All thirteen value base types and seven lane counts are
checked at both pointer widths, with explicit invalid encodings and construction
inputs. Storage extents retain complete vector widths; target restrictions are
separate from representation validity.

Checkpoint 2bfd320 extends the physical transfer path to sixteen-byte SIMD
values. Q loads/stores and full-width ORR moves preserve upper halves. Register,
stack and mixed cycles use separate reserved v31 cycle and v30 memory scratches,
with x16 for large addresses. GPR/cross-bank sixteen-byte values are rejected
without output mutation. Existing scalar scratch behavior is unchanged.

Focused native checks pass forty-eight cycle/fan-out/frame cases, including
65536-byte and unaligned65539-byte offsets and 4096-byte frame bias. Whole-buffer
comparisons check both halves and surrounding bytes; flags are retained. Four
protected source/destination boundary pairs verify exact accesses. Seven encoded
words match independent LLVM MC 23.1.4 output. Existing scalar transfers, anchored
and large-offset cycles, floating calls and aggregate results/recursion pass.

The next implementation gate is connecting actual vector values to graph
construction/validation, memory/phi operations, width-aware allocation and ABI
placement/results. Current graph/prototype interfaces continue to reject vector
types explicitly. This checkpoint is transport support, not an end-to-end vector
or compiler-backend claim. Optimization/scaling, remaining semantics, backend
integration and equivalent LLVM/TPDE measurements remain open.


Checkpoint ac1c094 writes one native Q-transfer wrapper as a Mach-O object and
executes it after linking from a separate Coil consumer. The four-way cycle
v0 -> unaligned slotA -> unaligned slotB -> v1 -> v0 uses offsets beyond the
Q-register immediate range and a 4096-byte frame bias. Complete buffer and flags
checks pass. The producer was rerun after adding object output; no library
implementation changed during the full regression run.


The vector transport checkpoint passes all 179 standalone checks and 46 linked
AOT consumers locally with debug checks and regenerated objects. Exact test-set
comparison verifies complete coverage without duplicates; linked output has no
warnings. The final AOT-output addition to the vector producer was verified by a
focused rerun during the complete standalone run, followed by all linked tests.
No library implementation changed during that run. Formatting and git diff checks
pass. All 321 implementation/test files remain Coil. Installed Coil d2a49bf21376
and Homebrew LLVM MC 23.1.4 were used on this arm64 Mac. Full vector graph/ABI,
backend and benchmark requirements remain open as described above.


### Mixed-width cycles and per-owner spill shapes

Checkpoint cdfdf14 adds a sized parallel-copy plan and native emission for mixed
4/8/16-byte edges. Cycle sources are retained at their complete read extent;
normal writes retain their edge width. One plan covers GPR, SIMD and stack
locations. Independent width groups would lose dependencies between aliased SIMD
registers. Reserved cycle, vector/scalar memory and address temporaries are
separate. Distinct stack identities are checked for overlap after sorting.

The planner passes729 byte-model cases, and native emission passes120 mixed
cycle/fan-out/frame cases with complete live extents and flags checked. A
separately linked Mach-O fixture crosses scalar GPR, full SIMD and unaligned
large stack locations in one cycle. Invalid shape, scratch, overlap and late
emission failures leave output unchanged.

Checkpoint 4700ed5 adds explicit parent-indexed spill geometry to allocation.
Every active virtual owner is checked before allocation begins. Children retain
their parent's shape, and evictions use the evicted owner's size/alignment.
The AArch64 bridge supplies explicit shapes; scalar storage remains eight bytes.
Normal graph split and CFG/Phi edge emission now uses the owning value's extent
through the mixed-width planner. Narrow values keep their normalized32-bit form.

Native tests force repeated evictions among three values sharing one SIMD
register, over all six permutations of4/8/16-byte storage and four seeds. They
verify frame alignment/prefix/padding, shared parent slot identity, all required
use payloads and flags. A linked fixture verifies the same spill/reload path.
Focused existing allocation, Phi, floating loops, GP/FP switch/bulk pressure,
aggregate results/recursion and numeric conversions pass.

A further reproducer for the installed Coil inline-vector Iterable diagnostic
was added to its existing open coil-bugs report. Iterating a bound collection
works; no Coil compiler source changed. The vector graph builder/verifier,
memory operations/constants, SIMD allocation class and ABI/HVA interfaces remain
to be enabled and verified. The full library/backend/benchmark goal remains open.


The mixed-width allocation checkpoint passes all181 standalone checks and48
linked AOT consumers locally with debug checks and regenerated objects. Exact
source/pass-set equality verifies complete coverage without duplicate runs;
linked output has no warnings. Library/test sources remained unchanged throughout
the complete run. Formatting and git diff checks pass. All326 implementation/test
files remain Coil. Installed Coil d2a49bf21376 was used on the arm64 Mac.
This establishes the copy/spill foundation, while vector graph/ABI support,
remaining semantics, optimization/scaling, the actual compiler adapter and
LLVM/TPDE runtime and compile-time measurements remain open.


### Vector graph transport and simultaneous Phi definitions

Checkpoint `6fcf587` connects vector memory and Phi values to graph construction,
structural/semantic checks, SIMD classes, per-parent allocation and native memory
emission. Checked load/store helpers reject malformed inputs before graph
mutation. Vector data use is distinct from control-chain dependency. Unsupported
vector arithmetic/ABI roles reject explicitly, even when dead. Native transport
supports 8/16-byte vectors; wider valid representations produce a target error.

Pressure testing exposed a preexisting scalar Phi defect, reproduced with forty
f64 Phis before the fix. Ranges, constraints and edge lookup treated each Phi's
textual schedule position as a separate register definition. Later definitions
could reuse earlier registers, although edge copies are simultaneous. The group
then contained multiple writes to v29. Phi ranges/destinations now use common
block entry, and a Phi may start in its own spill slot instead of requiring a
register at its textual position. Real uses still require registers. The scalar
reproducer and vector matrix pass; the physical-Phi unit also distinguishes its
entry stack slot from its later register location. Evidence is in the project pad.

Native checks pass 52 branch graphs (all 26 supported shapes, ordinary/volatile),
eight vector pressure graphs and the scalar f64 reproducer. They retain forty
SIMD and forty GPR values across register-clobbering calls, swap twenty vector
pairs through loops and check fixed/dynamic guards with 16/4096-byte frames.
Exact bytes include signed zeros, infinities and NaN payloads. Eight linked
Mach-O objects pass the branch/pressure interfaces. Checkpoint `c39735` adds 32
protected source/destination/branch placements and explicit wider-target rejection.
Aligned/unaligned source and destination checks accompany those boundary tests.

Next: upstream-shaped LONG_CONST storage/interning/materialization, vector
operations and vector/HVA argument/result roles. Compiler layout classification,
remaining wide/atomic/intrinsic/variadic-access semantics, optimizer/scaling,
actual backend integration and equivalent LLVM/TPDE runtime/compile-time
measurements remain open. No performance conclusion follows from these checks.


The vector graph checkpoint passes all 183 standalone checks and 49 linked AOT
consumers locally with debug checks and regenerated objects. Exact source/pass-set
equality confirms coverage without duplicate runs; linked output has no warnings.
Library implementation stayed fixed during the complete run. The aligned/source-
unaligned test refinement was verified before the run reached that producer, and
the final source passed in the complete run. Formatting and git diff checks pass.
All 330 implementation/test files remain Coil. Validation used installed Coil
d2a49bf21376 on the local arm64 Mac. The Phi correction, vector transport coverage
and remaining full-goal gates are recorded in the project pad.


### Upstream LONG_CONST vector payloads and shared materialization

Checkpoint e756f43 stores complete vector bytes with upstream LONG_CONST header,
payload ordering and hash semantics. Scalar/reference encodings are preserved.
Constant spans distinguish payload cells from values. Complete verification and
dumping understand variable extents; vector interning compares every declared
byte, handles collisions and retains references through growth. Invalid checked
construction does not mutate storage. Payload padding remains outside the value.

Checkpoint 8818a8d materializes supported native constants through owned private
image data, complete SIMD loads and shared ADRP/ADD relocations. Phi literals use
their real class/extent for registers and spill slots. Private data is aligned,
deduplicated by interned reference and retained after graph release. Byte-only
compilation still rejects unresolved references. JIT and Mach-O consume the same
image. Larger represented constants reject at the current native width boundary.

Storage checks cover all 182 type/target combinations, deliberate hash collisions,
mixed scalar/long chains, high-half differences, array growth, nonsemantic padding,
malformed cell/header/link/hash metadata and payload references. Materialization
checks reject invalid classes/widths/addresses before output mutation and invalid
payload hashes before reserving data. A mixed 5000-byte string/vector image checks
alignment and relocation coexistence and executes after mapping.

Native checks pass 61 graphs:52 direct/branch cases across all 26 native vector
shapes, eight 40-Phi loop/call-pressure variants at 16/4096-byte dynamic alignment,
and one 320-constant cross-page pool. Exact bits include zeros, infinities and NaNs.
Each image's data count, alignment, private symbols and deduplication are checked;
the graph is released before mapping. Thirteen object fixtures pass after linking,
including the 5120-byte pool. Existing scalar image, conditional, floating-Phi/loop,
physical-Phi and vector transport checks pass.

Next requirements remain vector operations/local objects and vector/HVA ABI,
compiler-specific source classification, wide/atomic/intrinsic/variadic access,
optimizer/verifier/scaling and performance work, actual Coil backend integration
and equivalent LLVM/TPDE compile-time/runtime measurements. The full goal remains
active; no speed conclusion follows from these correctness checks.


The vector constant checkpoint passes all 185 standalone checks and 50 linked
AOT consumers locally with debug checks and regenerated objects. Exact
source/pass-set equality verifies complete coverage without duplicate runs;
linked output has no warnings. Library and test sources remained fixed throughout
the complete run. Formatting and git diff checks pass. All 334 implementation/test
files remain Coil. Validation used installed Coil d2a49bf21376 on the local arm64
Mac. Evidence and the remaining full-goal requirements are indexed in the project
pad. These checks establish constant correctness, not performance parity.


### Vector local storage checkpoint

Vector VAR/VADDR/VLOAD/VSTORE now use complete target-aware type extents, with
ordinary and volatile D/Q accesses, literal materialization and mixed scalar/vector
views. Wider objects may be addressed through narrower views. Natural VAR
alignment propagates to actual SP alignment. Unit geometry checks cover all 91
vector types at both pointer widths; native tests cover 280 graphs and 27 linked
objects, including forty vector locals plus simultaneous GP/SIMD call pressure
and dynamic storage in ordinary/4096-byte frames.

Vector arithmetic remains unfinished. Short-vector/HVA ABI transport has separate
incoming, outgoing, literal and Darwin variadic JIT/AOT checks; omitted parameters,
named/recursive vector calls, mixed widths and pressure across vector results
remain. Full optimization/verification/scaling, remaining scalar/intrinsic/atomic
semantics, targets, actual compiler integration and equivalent LLVM/TPDE compile
and runtime measurements remain open.

Vector-local regression: all 191 standalone and 54 linked consumers pass with
debug checks, exact coverage, regenerated objects and no linked warnings. All
344 implementation/test files remain Coil. Formatting/diff checks pass.


### Vector binary arithmetic checkpoint

Integer vector ADD/SUB and logical AND/OR/XOR, plus floating ADD/SUB/MUL/DIV,
now have checked construction/verification, SIMD allocation requirements and native
AArch64 D/Q emission. Single 64-bit lanes use legal scalar SIMD/FP forms. Complete
constants use shared images. Validation covers 224 independent LLVM MC instruction
words, 610 matrix graphs and eight result/original-operand call-pressure graphs;
73 objects repeat representative paths through linked AOT.

Remaining vector operations include integer multiplication/division, shifts,
extrema/comparisons, unary/lane/shuffle/conversion families. Remaining ABI cases,
full optimization/verification/scaling, target/object features, actual Coil backend
and equivalent LLVM/TPDE runtime and compile-time measurements remain open.

Vector-binary regression: all 193 standalone checks and 55 linked consumers pass
with debug checks, exact coverage, regenerated objects and no linked warnings.
All 349 implementation/test files remain Coil; formatting/diff checks pass.


### Integer vector multiply/divide/remainder checkpoint

Integer MUL/DIV/MOD now extend the existing typed vector binary interface. Native
byte/halfword/word MUL uses AdvSIMD; 64-bit MUL and integer DIV/MOD expand per lane
using only reserved x16/x17. MOD re-extracts the original dividend and never
requires x30 or a hidden helper. Guard metadata and source/destination aliasing
are preserved. Staged emission remains transactional.

Independent checks cover 254 single-instruction and 1,905 expanded/lane words,
1,030 matrix graphs plus 44 call-pressure graphs, and 241 linked objects. Wider
integer oracles check signed extrema, overflow and zero divisors without host
undefined behavior. Remaining vector shifts/extrema/comparisons, unary/lane/
shuffle/conversion families, wider standalone semantics/optimization/scaling,
actual compiler integration and LLVM/TPDE runtime/compile-time measurements remain
open. Full regression passes all 193 standalone and 55 linked consumers, with
debug checks, exact coverage, regenerated objects and no linked warnings. All
349 implementation/test sources remain Coil; formatting/diff checks pass.


### Vector unary checkpoint

NEG/ABS/NOT, BSWAP and lane CTLZ/CTTZ/CTPOP now use checked unary construction,
one SIMD input constraint and complete D/Q native emission. FP sign operations
preserve exact payload bits. Counts preserve element boundaries and widths;
64-bit zero counts use reserved x16 lane transfers. Shared lane primitives retain
existing binary APIs and avoid duplicated encoders.

Checks cover 528 register cases/940 independent LLVM MC words, 396 matrix graphs,
24 result/original-operand call-pressure graphs and 168 linked objects. The pinned
upstream AArch64 emitter's vector ABS NIY is recorded as a source capability gap.
Remaining vector shifts/extrema/comparisons, lane/shuffle/conversion families,
further standalone semantics/ABI/optimization/scaling, targets/object features,
actual Coil backend and equivalent LLVM/TPDE compile/runtime comparisons remain
open. Full regression passes all 195 standalone and 56 linked consumers with
debug checks, exact coverage, regenerated objects and no linked warnings. The
final strengthened unary literal corpus also passes focused JIT/AOT reruns. All
354 implementation/test sources remain Coil; formatting/diff checks pass.


### Vector shift checkpoint

SHL/SHR/SAR now support same-type vector counts or broadcast integer scalar counts.
Both count classes use width masking consistently with scalar library semantics.
The native register sequence is three to five SIMD instructions independent of
lane count, with one reserved count workspace and correct GPR/SIMD input classes.
Valid-range reference behavior agrees; out-of-domain reference target differences
are documented rather than silently inheriting signed-byte hardware counts.

Checks cover 540 register cases/2,160 LLVM MC words, 2,940 matrix graphs, 60 pressure
graphs and 276 linked objects. Existing binary/unary matrices pass. Remaining
vector rotates/extrema/comparisons and lane/shuffle/conversion families, wider
standalone verification/optimization/scaling, ABI/target/object features, actual
compiler integration and equivalent LLVM/TPDE runtime/compile-time measurements
remain open. Full regression passes all 197 standalone checks and 57 linked
consumers with debug checks, exact coverage, regenerated objects and no linked
warnings. All 358 implementation/test sources remain Coil; formatting/diff checks
pass.


### Vector rotate checkpoint

ROL/ROR now reuse typed scalar/vector count forms and masking. General SIMD
sequences preserve an aliased data source in v30 after capturing counts in v31;
single 64-bit lanes use a shorter RORV sequence through reserved x16/x17. The body
is bounded independently of lane count and does not introduce hidden helpers.

Combined coverage: 4,900 matrix graphs, 100 pressure graphs, 176 forced-register
JIT harnesses and 460 linked objects. Rotate-specific checks add 480 register
cases/4,086 LLVM MC words. Remaining vector extrema/comparisons, lane/shuffle/
conversion families and the wider standalone/compiler/backend/benchmark goal are
still open. Full regression passes all 197 standalone checks and 57 linked
consumers with debug checks, exact coverage, regenerated objects and no linked
warnings. All 358 implementation/test sources remain Coil; formatting/diff checks
pass.


### Vector extrema checkpoint

MIN/MAX now use the shared typed vector builder/validation path for all Boolean,
integer/address and floating element types. Native D/Q emission uses signed or
unsigned SIMD min/max for 8/16/32-bit integer lanes and lane-wise CMP/CSEL for
64-bit integer lanes. Boolean vectors use unsigned byte lanes, preserving the
existing raw mask-byte representation. Floating lanes follow the existing scalar library contract:
choose left for ordered <= (MIN) or >= (MAX), otherwise right. This preserves
selected NaN payloads, including signaling bits, and the left zero sign on a tie.
The pinned reference AArch64 backend instead uses FMINNM/FMAXNM; those exceptional
semantics differ. No full exceptional-input equivalence is claimed.

FP vectors use FCMGE/BSL with a mask register distinct from both sources, including
when literals occupy both reserved SIMD registers. Single f64 lanes use FCMP/FCSEL.
All emission is staged before append; no helper calls or additional allocated
registers are needed. Native result registers exclude reserved v30/v31.

Focused validation covers 676 register cases / 1,860 independently assembled LLVM
MC words; 260 graph variants across all 26 D/Q types, both operations and five
loaded/literal/identical-input forms; 121 input-pattern pairs per matrix graph;
676 forced-register JIT harnesses; 32 call/spill pressure graphs with 16/4096-byte
frames and live dynamic storage; and 292 linked Mach-O objects. Selected result
bits, original operands, input memory and surrounding padding are checked.
Comparisons, lane/shuffle/conversion families, the remaining independent-library
work, actual compiler integration and LLVM/TPDE performance comparisons remain
open.


The final unchanged-source regression passes all 199 standalone checks and all
58 linked consumers with debug checks. The standalone pass regenerates fixtures
before linked validation; exact file/consumer pass sets match, and linked output
has no warnings. All 362 implementation/test files are Coil. Formatting and diff
checks pass. Current evidence is indexed in the coil-stogir project pad.


### Vector comparison checkpoint

The independent vector predicate module validates equal operand types, explicit
integer result masks with matching lane count/element width, and 4/8-byte target
pointer layouts. `builder.vector-compare!` takes graph, opcode, result mask type,
pointer bytes and the two operands. `vector-comparison.mask-type` computes a
canonical unsigned mask type for an operand type and pointer width; matching
signed, Boolean-byte and address mask types are also accepted.

Integer EQ/NE, signed LT/GE/LE/GT and unsigned ULT/UGE/ULE/UGT use lane bit-width
semantics independently of the declared integer signedness. Floating comparisons
implement all twelve scalar-library predicates, including unordered U-prefixed
relations and ORDERED/UNORDERED. True lanes are all ones, false lanes zero.
Scalar floating classification now excludes vector predicates so valid masks do
not enter scalar Boolean validation. The generic vector verifier, SIMD constraints
and native dispatch consume the separately typed input/result roles.

D/Q emission uses one SIMD comparison for basic relations, inversion for NE and
unordered-inclusive predicates, and paired self-comparisons/AND for orderedness.
An aliased input is saved before the two comparisons; v30 is reused only after
its input is consumed. Literal inputs may occupy either reserved SIMD register.
All emission is transactional and needs no helper calls or per-lane loops.

Pinned upstream AArch64 vector U-prefixed floating paths use ordered FCMGT/FCMGE,
whereas scalar paths include unordered inputs. Its vector ORDERED/UNORDERED route
has no matching emission case and reaches NIY in assertion builds. This library
uses consistent scalar predicate semantics; source capability differences are
recorded in the project pad and do not imply full exceptional-input equivalence.

Focused checks cover 3,484 register cases / 4,346 independent LLVM MC words, all
91 abstract vector type codes and matching integer mask representations, target
pointer-width geometry, 1,340 native graph variants with 121 pattern pairs each,
3,484 forced physical-register JIT harnesses, 56 clobbering-call/spill/dynamic-frame
pressure graphs and 860 linked Mach-O objects. Remaining lane/shuffle/conversion
families, broader independent-library coverage/optimization/scaling/targets, the
actual Coil compiler backend and equivalent LLVM/TPDE runtime/compile-time
benchmarks remain required.


The unchanged-source comparison regression passes all 201 standalone checks and
all 59 linked consumers with debug checks, regenerated objects, exact expected
file/consumer pass sets and no linked warnings. All 367 implementation/test files
remain Coil. Formatting/diff checks pass; the project pad indexes the evidence.


### Vector lane transport checkpoint

EXTRACT, REPLACE and SPLAT now have target-width-aware checked builders and generic
verification over all 91 vector representations. Floating scalar types match the
vector base exactly; integer scalar types may reinterpret equal-width lane bits.
The three builders take the result scalar/vector type and pointer-byte width;
EXTRACT/REPLACE also take a scalar integer index. Numeric constant indices outside
the lane count reject before graph mutation. Dynamic indices are compared unsigned;
out-of-range extraction returns zero, and replacement preserves the input vector.
These invalid-index results are a defined library extension, not equivalence with
the reference's unchecked dynamic memory indexing. Boolean lanes retain raw byte
bits, consistent with vector transport; explicit Boolean conversions can canonicalize.

AArch64 D/Q constant extraction uses UMOV/SMOV or scalar DUP, replacement uses INS
after any required full-width copy, and splat uses DUP or the singleton-D transfer.
Dynamic extraction constructs bounded table indices and uses TBL. Dynamic
replacement forms a lane-byte mask with precomputed lane-ID words and BSL. Neither
path adjusts SP, branches, calls a helper or accesses memory through the index.
The typed native adapter captures data, dynamic index and replacement bits before
result writes; reserved x16/x17 and v30/v31 carry the prepared workspace. Scalar
results keep their correct GPR/FP class. Emission stages bytes and references before
append, and VAR/ARGVAL wrappers cannot be used as lane values.

Focused validation passes 2,976 register cases / 9,309 LLVM MC words, abstract
32/64-bit geometry and rejected construction checks, 4,006 JIT matrix graphs,
328 forced-register harnesses, 60 clobbering-call/spill/dynamic-frame pressure
graphs and 1,490 linked objects. Integer extraction is also widened and checked
for signedness; FP payloads, original values/counts, input memory and padding are
checked exactly. The remaining shuffle/vector-conversion families and broader
standalone/compiler/backend/benchmark work remain required.
