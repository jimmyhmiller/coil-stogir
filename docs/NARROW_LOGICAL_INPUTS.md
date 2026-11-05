# Narrow bitwise operands use original registers

For byte/halfword AND, OR and XOR, emit the existing32-bit logical instruction
from original physical operand registers and retain the existing signed or
unsigned result extension. Low-k-bit truncation commutes with these bitwise
operations; arbitrary upper bits cannot influence the result. This avoids one
input extension for immediate forms and two for register forms. It needs no
canonical-value assumption, analysis cache, unchecked semantic flag or changed
ABI. Arithmetic, comparisons, shifts, rotates and final normalization are
unchanged. Allocation still sees the original graph uses and definitions.

This follows the pinned upstream AArch64 ir_emit_binop_int direct logical
register selection in spirit; it retains Coil's own result-width contract.
The proof and implementation are independent. Existing LICENSE/NOTICE apply.

Debug/ASAN validation: jit-bitwise, narrow-binary-object plus linked
 aot-narrow-binary-link, jit-loop-guard and jit-loop-vectorize pass. New direct
native emitter cases call through full-u64 ABI operands with arbitrary upper
bits for bool/u8/u16/char/i8/i16 and all three logical operations, aliasing the
destination with either input or neither. Independent bitwise-and-mask/sign
extension oracles check returned bits. Existing full graph immediate/register
selection and original-live-operand tests remain enabled.

The previously dormant logical-native-check test contained self-recursion in
its initial failure count and was not called by main. The accumulator now starts
at zero and main runs it:6636 independently enumerated hardware logical masks
with three operations and five input patterns. This corrects test coverage,
not a Coil compiler defect. No bootstrap performance claim is established.


A small diagnostic using1M opaque416-byte copies, same independent caller and
byte oracles,8 rotating CPU samples after warmup: aligned prior late7.9350ms,
new7.1695ms, LLVM5.6885ms. At alignments1/7/15 prior7.9255/7.9465/7.9595ms,
new7.4730/7.4715/7.4500ms, LLVM6.0280/5.9820/5.9610ms. Evidence and source hashes
are in validation/narrow-logical-inputs. This is still outside10% on this kernel.
The late-widening compiler integration is rejected independently; this general
emission change must be tested separately on the retained scalar baseline.
