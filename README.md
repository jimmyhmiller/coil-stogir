# coil-stogir

A standalone Coil implementation in progress of [dstogov/ir](https://github.com/dstogov/ir),
followed by a Coil compiler backend. Fast code generation, JIT, and AOT are core
requirements. All library and test implementation sources are Coil.

The standalone library currently compiles a subset of scalar graphs to
native macOS AArch64 code. It includes graph construction and local folding,
CFG/dominance analysis, placement, scheduling, split-interval register allocation,
spill handling, phi transfers, arithmetic, comparisons, branches, typed
singleton/range/default switches with dense jump tables, trap/unreachable
paths, loops, memory
accesses, integer/address conversions and bitcasts, scalar integer binary arithmetic/logic/shifts/rotates, MIN/MAX and conditional
selection, checked ADD/SUB/MUL with overflow projections, scalar unary operations
(negation, complement, absolute value, byte swap and bit counts), and direct/indirect calls with register and stack arguments.
Graph-owned function/callee prototypes support incoming stack parameters, omitted
projections, narrow register/stack calls and results, void returns, and Darwin
integer and floating variadic calls, including f32-to-double promotion. Floating
parameters/results and mixed GPR/SIMD calls are supported, along with floating
ADD/SUB/MUL/DIV, NEG/ABS, predicates, extrema, memory, bitcasts and phi values.
Numeric FP conversions, scalar truth tests and mixed-bank conditional selection
are also supported. Tests execute generated functions through JIT and linked Mach-O objects. The shared
image writer supports text/data, local/exported/undefined symbols, and pointer,
branch, and page relocations. Named function/data references and binary string
literals compile through this shared image, including recursive calls.
Module composition resolves public declarations, renames private symbols and
remaps relocations across independently compiled functions and data.
Shared images retain global/code alignment through composition, JIT layout and
Mach-O section declarations, with checked target limits.

Scalar/vector local storage supports VAR, VADDR, VLOAD/VSTORE and their volatile
variants, with typed views that fit the declared object and power-of-two
alignment. Local objects have separate identities from register spills; addresses
can survive calls and spilling. ALLOCA/AFREE support constant and dynamic byte
counts with matching frame-alignment rounding, nested objects and calls.
BLOCK_BEGIN/BLOCK_END save and restore whole dynamic stack scopes; snapshots
survive register spills and calls while fixed storage stays anchored.
Over-aligned frames preserve entry SP for incoming arguments and exact restoration.
Explicit `builder/frame-object!` declarations support fixed positive-extent
function-lifetime objects without changing raw ALLOCA/SP-snapshot semantics.
The first native stage retains address registers; rematerialization is unfinished.
See [static entry objects](docs/STATIC_ENTRY_ALLOCATIONS.md).
FRAME_ADDR establishes a real frame record, including in leaf functions; fixed
storage accesses then use an explicit x29-based frame context.

ARGVAL supports indirect aggregate arguments through private aligned copies at
call time, including repeated arguments, stack-passed pointers and variadic
calls. Grouped integer pairs and homogeneous f32/f64 pieces share incoming/outgoing ABI
placement, including bank exhaustion and variadic packing. Explicit result-storage
roles support integer and homogeneous floating register results and x8 indirect
results. Additional classification/vector coverage remains unfinished.


Internal 64/128-bit vector loads/stores and branch/loop Phi values now preserve
complete SIMD payloads through spills, clobbering calls and aligned dynamic
frames in JIT and linked AOT. Vector constants follow the upstream LONG_CONST
layout and use aligned private image data. Short-vector/HVA call plumbing now
preserves complete SIMD argument/result pieces. Native JIT and linked AOT checks
cover one through four members, bank exhaustion, stack/literal arguments and
Darwin variadic packing against LLVM C calls. Vector integer ADD/SUB/MUL/DIV/MOD and AND/OR/XOR, plus floating
ADD/SUB/MUL/DIV, now have
native and linked coverage. Vector NEG/ABS/NOT, byte swap, lane bit counts and SHL/SHR/SAR with vector or
scalar counts, plus ROL/ROR with protected source aliases, have native and linked
coverage. Lane-wise integer and floating MIN/MAX also have native and linked
coverage. Floating extrema select the left operand on an ordered tie and the
right operand for unordered inputs, preserving exact payloads and zero signs.
Integer and floating vector comparisons return checked full-lane integer masks;
floating U-prefixed predicates include unordered inputs, matching scalar rules.
EXTRACT/REPLACE support checked constant and dynamic lane indices, and SPLAT
transports complete scalar bits. Dynamic lane access stays in registers.
Scalar conditions can also select complete vector values through COND, with
bit-preserving native mask selection and the existing truth/folding/CSE rules.
Equal-storage-size scalar/vector and vector/vector BITCAST preserves complete
literal and runtime payloads, with native D/Q transfers and symbolic address
relocations. A Coil extension supplies sequentially consistent U8/U16/U32/U64 atomics: load,
store, ten RMW operations, compare/exchange and fence. Native RMW/CAS requires
AArch64 FEAT_LSE. Remaining vector operations and broader ABI coverage are unfinished.

Native copy, overlap-safe move and zero builders expand into existing memory
and control nodes. Fixed small transfers use exact-width accesses; larger and
dynamic operations use bounded loops. See the [bulk memory API](docs/MEMORY.md).

This is an incomplete port. Full optimization and scalar/vector coverage,
further control/intrinsic semantics, variadic argument access,
additional special constants, object features/targets, compiler integration,
and runtime/compile-time comparisons with LLVM and TPDE remain unfinished.
See the [architecture and delivery plan](docs/PLAN.md), [control-flow contracts](docs/CONTROL.md),
[ABI coverage](docs/ABI.md), and [image/JIT/AOT APIs](docs/IMAGES.md).

Run a check locally, for example:

```sh
coil run tests/verify.coil --debug-checks
```

Executable checks in `tests/` cover graph invariants, analysis, allocation and native
execution, including loops and register pressure. JIT checks require macOS AArch64.
Passing these checks does not establish full upstream compatibility or performance.

coil-stogir is licensed under the [MIT License](LICENSE). It is ported and adapted
from **[Dmitry Stogov's IR](https://github.com/dstogov/ir)**, originally
copyright Zend by Perforce and Dmitry Stogov, distributed under the **MIT License**.
See [LICENSE](LICENSE), [NOTICE](NOTICE), and the
[source provenance and credits](docs/PROVENANCE.md). These notices must accompany
library distributions and later vendoring into Coil.

The `3a62f49` scalar-selection checkpoint passes 211 standalone checks and 65
linked AOT consumers on a fixed toolchain with regenerated objects and unchanged
validation inputs. It adds LLVM-MC-checked constant shift encodings, 208 constant
shift/multiply JIT graphs, and conversion checks with the original operand live.
Full optimized-pipeline parity is still missing; the architecture audit in
[PLAN.md](docs/PLAN.md) lists the upstream pass order and current gaps.

The `dc90b58` construction checkpoint also passes the complete 211 standalone /
65 linked AOT regression on unchanged inputs and a fixed toolchain. Commutative
operand ordering and truncation-of-extension folding now follow pinned upstream
construction rules. SCCP, persistent matching/fusion before liveness, coalescing
and block-scheduling parity remain open architectural work.


Post-allocation block-layout checks include a transcript mode for comparing the
same CFG facts with the pinned upstream scheduler:

```sh
coil run tests/block-layout.coil --debug-checks -- --oracle
```

The [recorded comparison](docs/validation/block-layout-oracle.json) has 59 matching
block orders/alignment decisions. This is scheduling-core evidence, not complete
optimizer parity. The shared-image AOT consumer now uses both image fixtures:

```sh
coil run tests/macho-image.coil --debug-checks
coil run tests/jit-branch.coil --debug-checks
coil run tests/aot-image-link.coil --debug-checks --link-flag /tmp/coil-stogir-image.o --link-flag /tmp/coil-stogir-long-relocated-branch.o
```

The SCCP value-domain port can be checked independently:

```sh
coil run tests/sccp-values.coil --debug-checks
coil run tests/sccp-values.coil -- --oracle
```

The [value-domain comparison](docs/validation/sccp-values-oracle.json) records
state/queue agreement with the pinned reference, including dependent copy
partition splits and exact constant payloads. This is a prerequisite for SCCP;
it does not enable SCCP in the compiler. Development analysis and graph rewriting
now have pinned-reference and native execution checks. Remaining folding,
follow-up iterative optimization, mode policy and compiler delivery are pending.

Whole-node graph rewrites keep existing references fixed, clear construction
CSE, and expose released continuation cells as NOPs. They reject requests that
do not fit the original allocation. The owning optimizer must remap incoming
edges/roots and rebuild analysis caches. SCCP is not enabled by these APIs.

Native pressure coverage includes simultaneous Phi definitions with reverse
use order, checking spilled prefixes on both branch paths. Its AOT fixture is
consumed together with the existing pressure cases:

```sh
coil run tests/jit-pressure.coil --debug-checks
coil run tests/jit-switch-pressure.coil --debug-checks
coil run tests/aot-switch-pressure-link.coil --debug-checks --link-flag /tmp/coil-stogir-switch-pressure-gp.o --link-flag /tmp/coil-stogir-switch-pressure-fp.o --link-flag /tmp/coil-stogir-phi-pressure.o
```

The development SCCP rewrite uses an owned copy of the same graph, preserves
explicit data roots, compresses region/Phi inputs together and unlinks unreachable
terminal-list members. Callers must rebuild graph analyses before code generation.
The execution checks compare original/transformed functions and verify COPY
payloads after graph storage is released:

```sh
coil run tests/jit-sccp-rewrite.coil --debug-checks
coil run tests/jit-sccp-control.coil --debug-checks
coil run tests/sccp-rewrite-errors.coil --debug-checks --sanitize=address
coil run tests/aot-sccp-rewrite-link.coil --debug-checks --link-flag /tmp/coil-stogir-sccp-dynamic.o --link-flag /tmp/coil-stogir-sccp-false.o --link-flag /tmp/coil-stogir-sccp-true.o --link-flag /tmp/coil-stogir-sccp-payload.o
```

The first command generates all four objects for the linked consumer. These are
component checks; the optimizer remains disabled in the delivered Coil backend.

Tail-call checks (native macOS AArch64):

```sh
coil run tests/jit-call.coil --debug-runtime --sanitize=address
coil run tests/aot-call-link.coil --debug-runtime --sanitize=address --link-flag /tmp/coil-stogir-call.o --link-flag /tmp/coil-stogir-tail-recursive.o
```

The first command creates both AOT fixtures used by the second.
