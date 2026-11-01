# Source provenance and credits

coil-stogir is a Coil port and adaptation of Dmitry Stogov's
[IR — Lightweight JIT Compilation Framework](https://github.com/dstogov/ir).
The reference checkout is pinned to
`92171d0a4a36b0acf707f2dea7998de615dd4acd`.

[LICENSE](../LICENSE) retains upstream's MIT permission/disclaimer text and both
copyright notices, with a copyright notice for the Coil implementation added.
[NOTICE](../NOTICE) identifies the upstream author, source, revision, and design
acknowledgments. Licensing and attribution are kept in these central files.

## Reference map

This map records derivation and design references. It does not claim a complete,
line-for-line translation of each upstream pass or equivalent behavior.

| Coil area | Upstream source / relationship |
| --- | --- |
| `types`, `node`, `opcode` | Scalar encoding, cell layout, opcode ordering and metadata from `ir.h` |
| `graph`, `builder`, `fold`, `integer-unary`, `integer-binary`, `conditional`, `checked`, `conversion`, `numeric-conversion`, `floating` | Construction, signed references, constants, and integer folding adapted from `ir.h`, `ir.c`, `ir_builder.h`, `ir_fold.h` |
| `calls`, `prototype-bytes`, `symbols`, graph string table | Prototype bytes, FUNC/FUNC_ADDR header annotations, FUNC/SYM/STR address constant layout, PROTO annotation, interned string identity, and control-pinned CALL shape follow `ir.h`, `ir.c`, `ir_builder.h`; the binary arena/hash implementation is Coil code |
| `verify`, `dump` | Validation and diagnostics developed against `ir_check.c` and `ir_save.c`, including DIV/MOD control-guard validation; dump format is currently different |
| Uses, CFG, dominance, loops, placement, scheduling | Pipeline developed against `ir_cfg.c` and `ir_gcm.c`; current natural-loop analysis and scheduling are incomplete |
| Liveness, ranges, constraints, allocation, phi/edge moves | Split-interval and SSA allocation work guided by `ir_ra.c` and its algorithm references; exact-subposition transfer indexing is Coil code; not yet upstream allocator parity |
| Terminal control | TRAP/UNREACHABLE and optional START/terminal-list links follow `ir.h` and `ir.c`; UNREACHABLE retains its reserved second slot. Shape/type checks and linear terminal-chain validation are Coil implementations. TRAP emits the reference AArch64 BRK; this target gives UNREACHABLE an explicit breakpoint/re-entry sequence. |
| Switch dispatch | SWITCH and CASE_VAL/CASE_RANGE/CASE_DEFAULT shapes follow `ir.h`, `ir.c` and `ir_builder.h`; `ir_aarch64.dasc` is the target reference. Signed order-key normalization, heapsort validation, balanced range decisions and case edge-transfer stubs are Coil implementations. Dense singleton selection follows the upstream count/span rule; signed 32-bit relative tables replace its full-address entries, retaining the same dispatch/control model. |
| Scalar locals and frame layout | VAR/VADDR/VLOAD/VSTORE, FRAME_ADDR, ALLOCA/AFREE and BLOCK_BEGIN/BLOCK_END metadata and access behavior follow `ir.h`, `ir_ra.c` and `ir_aarch64.dasc`; separate local/spill maps, SP/x29 contexts, outgoing-prefix layout, saved-entry-SP realignment and count-domain guards are Coil code; allocation/free consistently round original counts to the function alignment (minimum sixteen), unlike the qualified upstream dynamic-AFREE source concern |
| AArch64 selection/emission and ABI | `ir_aarch64.dasc` is the target reference; current Coil encoders emit words directly rather than using DynASM; typed scalar truth and floating comparison conditions (with consistent compare/select extrema), conversion sequences (with canonical Boolean destinations), checked-overflow conditions/sequences, DIV/MOD/ROL, MIN/MAX/COND and scalar unary sequences are adapted with explicit scratch handling; unary population count encodes both SIMD register fields |
| Bulk memory construction | Independent Coil expansion into the upstream-shaped LOAD/STORE, loop, branch and PHI nodes. Exact-width chunks, small-move snapshots and bounded forward/backward loops are implemented here; no upstream or TPDE bulk-copy implementation is imported. |
| Module image composition | Independent Coil implementation over the shared image model: public definition binding, private namespace isolation, stable per-input ID maps, section/relocation/text-data rebasing, per-section alignment propagation and immutable input validation. |
| JIT images, relocation planning, Mach-O writer | Coil implementations of a shared text/data image with symbol binding, ABS64/branch/page relocations, and Mach-O serialization; format references are Apple SDK headers and LLVM MC object output, with no SDK or LLVM source vendored. Data-in-code spans preserve relative jump-table metadata, with MH_OBJECT VM-offset entries and u16 length splitting. Aligned section VM layout was checked against LLVM MC output; checked reservation/protection layout and original-mapping release tracking are Coil implementations. Named FUNC/SYM/STR graph lowering uses shared image relocations; additional formats/features remain unfinished |

The current graph uses separate contiguous arrays for instructions and constants.
The current allocator, fold rules, target coverage, verifier, and optimization
pipeline remain incomplete. See [PLAN.md](PLAN.md) for the delivery gates.

## Additional references and distribution

The neighboring coil-tpde package demonstrates the independent library followed
by a compiler backend. TPDE/coil-tpde target and object code has also been consulted
as reference material. This package currently vendors/imports no TPDE modules.
TPDE and its contributors have a separate Apache-2.0 WITH LLVM-exception license;
MIT attribution for IR cannot replace that license if TPDE source is adapted in
future work. Preserve file-specific notices when introducing any such source.

The current package uses Coil's standard library and native platform APIs; it
ships no upstream C implementation or DynASM source/generated action tables.
Compiler, runtime, or other dependencies bundled in a future binary release need
their own applicable notices. Packaging this library must include `LICENSE` and
`NOTICE`, together with any later third-party license files. A future Coil backend
vendor/import step must carry these files into Coil along with the source.

Keep this map current as more upstream modules are ported or
other source is reused. Attribute algorithm and design references separately from
copied or translated source so their roles remain clear.
