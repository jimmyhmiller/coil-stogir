# Per-node operand metadata in def-use walks

Pinned upstream ir.c:ir_build_def_use_lists reads instruction flags once per
node, outside its operand loop. Our use builder now reads one opcode metadata
word per node and decodes that retained word across its operands. The public
operand-code API still validates the opcode; operand-code-word decodes a cached
word with the same nonpositive-index and repeating fifth-field semantics.
Invalid opcodes still produce no reference kinds in the use builder.

All five fields are retained. We do not substitute upstream input-prefix counts,
which would drop our additional label/control reference edges. Count/fill order,
reference categories, range offsets, edge positions and mutation behavior remain.
Graph storage is only read in these walks; no graph pointer survives mutation.

The frozen independent textual metadata oracle checks131 opcodes, invalid opcode
and index bounds, and index65535/repeating-tail behavior. ASAN/debug opcode,
uses, mutable-use, native switch matrix and verifier checks pass. The opaque
materialized-edge checksum passes with stogir, LLVM and TPDE objects. The stogir
uses.build assembly shrinks573→554 listing lines in this reduction, with7 call
sites in both. This is a code-shape observation, not a runtime claim.

Runtime/generation measurements remain pending while the preceding bulk-init
Coil delivery completes its gate; do not time beside that gate/install.
