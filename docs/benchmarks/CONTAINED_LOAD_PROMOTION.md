# Contained integer loads across joins

Based on operand-control diagnostic 6276c01. The byte-order-independent promote!
API retains exact-width behavior. promote-ordered! adds an explicit target
little-endian policy and is selected by optimize-memory's existing byte-order
argument. No target endian is inferred from the host.

A private field uses the widest same-start integer access as canonical storage.
All stores must define the complete canonical width. Narrow integer loads become
TRUNC after the ordinary demand-driven SSA/Phi construction. Differently sized
BOOL/pointer views, floating views, displaced overlap, escapes, volatile/atomic
accesses and missing incoming initialization retain the existing memory path.
Same-width scalar BITCAST behavior is retained.

Debug-checks plus ASAN: tests/jit-mem2ssa.coil passes 52 new policy configurations
and 2106 native answers over joined fields, signed/unsigned views, high bits,
partial-store rejection, uninitialized-edge rejection and unspecified byte order.
Native executions cover O1/O2/O3. Existing 2115 late-forward cases, 1254 scalar
view answers and 36 branch-forward configurations also pass.

Compiler integration and controlled performance measurement are pending. No
bootstrap performance claim or global installation change.
