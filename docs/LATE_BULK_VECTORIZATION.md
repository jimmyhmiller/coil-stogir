# Scalar templates, late guarded copy vectorization

Restore the exact scalar bulk lowering from74530b8. Keep checked internal-vector
cloning ffdfc1f for explicitly supported vector SSA. Eager bulk-vector45fc238 and
its compiler integrations are rejected experiments: local copy improvement did
not translate to full-bootstrap benefit. Scalar combined88e09ce2 remains the
comparison checkpoint. The late copy counter normalization is now implemented in loop-byte-copy.coil.

The next pass belongs after module inlining and memory optimization, in the
existing O3 guarded-vectorization epoch. Ordinary graph LOAD/STORE loops have
observable ordering, including overlaps; memcpy's API nonalias precondition is
not automatically recoverable from a generic lowered loop. Never widen a loop
based only on its apparent copy shape. Reuse guards/scalar fallback or prove an
adequate no-hazard case.

The existing loop recognizer assumes unit element induction. Bulk's main loop
advances a byte index by8. A possible normalization must prove initial and bound
are multiples of8 (zero initial and a constant/masked aligned bound), preserve
all original byte-index values and observations, and make unit element induction
plus byte-address scale8 explicit. Preserve header/Phi predecessor associations,
comparison truth, zero counts, no-wrap bounds and original fallback semantics.
The existing affine/alias guard then reasons in its expected element units.

A changed graph ends its analysis epoch; CFG, ownership, uses and dominance must
be rebuilt before subsequent recognition. Normalization alone must not consume
the original header's only vectorization visit. Unsupported/backward/complex
loops retain the scalar form. No semantic flag, synthetic nonalias promise or
unchecked public path is introduced.

Validate small byte/guard/alias counterexamples before another compiler build.
Whole-bootstrap success still requires5× generation and runtime within10% of
LLVM O3; none of the eager-vector checkpoints meets those requirements.


## Implemented counter normalization and first measurement

The checked pass recognizes a zero-based unsigned byte counter advancing by8,
an aligned constant/masked bound, and an exact forward load/store backedge.
It preserves original byte-valued references as element-counter times8 and
preserves header predecessor associations. The existing late vectorizer supplies
alias guards, vector prefix and scalar fallback. It does not infer nonaliasing
from the copy shape. A changed graph is prepared again with fresh analyses.

Debug/ASAN native tests compare complete buffers to an8-byte load-before-store
oracle for overlapping and unaligned ranges, reversed predecessor slots, zero
and short null-pointer cases, and byte-counter liveouts. Unsupported stride,
bound, backward, volatile and altered-store shapes are rejected. The expanded
O3 bulk suite reports zero byte-comparison failures, including guard pages.

First small-case measurement, before constant-folding the new counter bound:
1M opaque416-byte copies; eight rotating process-CPU samples after warmup,
same independent C caller and full source/destination byte checks.

| Alignment | Scalar ms | Late vector ms | LLVM O3 ms |
|---|---:|---:|---:|
|0|16.7000|8.8395|5.4870|
|1|16.8810|8.8905|5.7960|
|7|16.9560|8.9430|5.9280|
|15|16.6650|8.8825|5.9510|

This improves the scalar case but remains outside the10% runtime target even
on this kernel. Assembly exposes substantial unfurled guard arithmetic after
late vectorization. Evidence is in validation/late-bulk-vectorization. No
compiler bootstrap adoption or goal achievement is claimed.


## Checked folding of generated guards

Guard binary construction now uses the existing checked integer binary/compare
builders instead of raw pure emits. This folds constant predicates and address
arithmetic without deleting any address-range or alias precondition. It does
not add another whole-graph optimization transaction. Dynamic inputs retain the
same predicates. The independent i128 interval oracle, vector prefix suite,
captured stencil suite, O3 bulk memory suite and linked AOT guard suite all pass
with debug checks and ASAN.

A fresh eight-sample run measured aligned scalar17.5765ms, late7.7345ms and
LLVM5.6300ms. At alignments1/7/15: scalar17.6355/17.4915/17.4005ms;
late7.8515/7.8850/7.9130ms; LLVM6.0055/5.9435/5.9075ms. Compare backends within
this run; system conditions differ from prior runs. The late object assembly
listing shrinks from133 to103 lines. Raw results include all library source
hashes. This is still outside the10% kernel runtime target and supplies no
whole-bootstrap performance evidence. Compiler integration remains pending.
