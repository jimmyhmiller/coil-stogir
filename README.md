# coil-stogir

A standalone Coil implementation in progress of [dstogov/ir](https://github.com/dstogov/ir),
followed by a Coil compiler backend. Fast code generation, JIT, and AOT are core
requirements. All library and test implementation sources are Coil.

The standalone library currently compiles a subset of scalar graphs to
native macOS AArch64 code. It includes graph construction and local folding,
CFG/dominance analysis, placement, scheduling, split-interval register allocation,
spill handling, phi transfers, arithmetic, comparisons, branches, loops, memory
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

Scalar local storage supports VAR, VADDR, VLOAD/VSTORE and their volatile
variants, with typed views that fit the declared object and alignment up to
16 bytes. Local objects have separate identities from register spills; addresses
can survive calls and spilling. ALLOCA/AFREE support constant and dynamic byte
counts with matching sixteen-byte rounding, nested objects and calls. Over-aligned
frames still require further frame lowering.
FRAME_ADDR establishes a real frame record, including in leaf functions; fixed
storage accesses then use an explicit x29-based frame context.

This is an incomplete port. Full optimization and scalar/vector coverage,
further control/intrinsic semantics, variadic argument access,
additional special constants, object features/targets, compiler integration,
and runtime/compile-time comparisons with LLVM and TPDE remain unfinished.
See the [architecture and delivery plan](docs/PLAN.md), [ABI coverage](docs/ABI.md), and [image/JIT/AOT APIs](docs/IMAGES.md).

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
