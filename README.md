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
