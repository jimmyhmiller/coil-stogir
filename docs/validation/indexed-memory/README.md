# Register-offset memory preparation

The pinned upstream 92171d0 ir_aarch64.dasc ir_match_fuse_addr only fuses constant
ADD offsets. Register-offset fusion is an independent target extension, not a
claimed upstream port. It belongs in the persistent matcher before liveness,
without rewriting the semantic graph or changing the upstream pass order.

Whole compiler source01f47440 object static disassembly has15916 adjacent register
ADD/memory pairs versus616 in LLVM. This is an opportunity count only: some
addresses are shared, scales unsupported, or code cold. It proves neither legal
fusion count nor speed. The observed profiled arena-vector helper contains a
scaled index ADD immediately followed by its load.

This preparatory checkpoint implements a read-only full-word base/index selector
and checked UXTX register-offset encodings. Optional SHL absorption requires the
exact storage-size scale and a full-width input. Other shifts stay explicit.
COPY remains a barrier; bounded word BITCAST views may be bypassed. Invalid
widths, missing references and non-word inputs decline. Existing constant-offset
selection remains unchanged.

128 instruction words independently checked against LLVM MC: unsigned GP
byte/halfword/word/doubleword load/store, signed byte/halfword W loads, FP32/64
and Q128 load/store; scaled/unscaled, SP/ZR, aliases. Invalid width/register/sign
combinations rejected. Encoder tests pass LLVM O1/debug/ASAN and Stogir O3/debug.
Selector geometry and existing JIT address suite pass LLVM O1/debug/ASAN.

NOT integrated into matching/allocation/emission yet. No generated-code change,
performance gain, compiler adoption or whole-bootstrap claim. Next: persist
selected index/scale; substitute base+index machine uses before liveness; retire
only genuinely unused address/shift nodes; preserve roots/shared uses; handle
base/index/value spill scratch conflicts; differential native tests for both
loads and stores, volatile accesses, SIMD, aliases and high pressure. Only then
measure representative emitter and compiler paths. Full goal remains5x
IR-to-machine-code speed and compiler runtime within10% of LLVM O3.
