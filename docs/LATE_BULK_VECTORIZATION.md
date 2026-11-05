# Scalar templates, late guarded copy vectorization

Restore the exact scalar bulk lowering from74530b8. Keep checked internal-vector
cloning ffdfc1f for explicitly supported vector SSA. Eager bulk-vector45fc238 and
its compiler integrations are rejected experiments: local copy improvement did
not translate to full-bootstrap benefit. Scalar combined88e09ce2 remains the
comparison checkpoint. No late copy transformation is implemented by this commit.

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
