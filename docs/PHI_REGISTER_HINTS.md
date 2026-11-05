# Phi register affinity experiment

Based on bulk-expansion `0d6d545`. Pinned upstream `ir_ra.c` records Phi use
reference hints and tries preferred registers when legal. The port already had
COPY/conversion hints and contained-copy coalescing, but no Phi edge affinities.
This adds conservative single-reference preferences using the existing Part
hint/recent-register mechanism; it is not full upstream multi-use hint parity.

After existing COPY/conversion preference setup, each scheduled Phi can prefer
its first positive same-bank input, and an incoming value with no existing hint
can prefer the Phi. Coalesced refs resolve through the existing alias map.
Constants/self references and values without allocation parts are skipped.
No range, union, mandatory register, spill policy or edge-copy semantics change.
Hint cycles are advisory reads of last-register fields, not recursive lookups.
The existing full-lifetime availability check can reject any hinted register.

The native jit-loop oracle passes with debug checks and AddressSanitizer. Its
summation loop loses one register transfer per iteration: ADD x1,x2,x1 followed
by MOV x2,x1 becomes ADD x2,x2,x1. Text shrinks from48 to44 bytes. Independent
unoptimized/optimized assembly is archived under validation/phi-register-hints.
No verifier or whole-compiler performance gain is established yet.
