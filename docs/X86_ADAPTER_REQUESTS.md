# What the Coil adapter needs from the x86-64 call ABI

Requests from the Coil compiler's Stogir adapter (Coil branch `stogir/x86`,
commits d2dc55e8..05cddcc6, 2026-11-10). The adapter hard-errors on each
shape until the library provides it. The System V call work implements these.

1. **Incoming MEMORY parameter (blocking).** A by-value aggregate parameter of
   class MEMORY lives in the caller's outgoing stack area. The adapter needs a
   prototype record `{ordinal, size, alignment}` that makes that ADDR PARAM the
   address of the caller's stack copy and consumes no register. The standard
   library's `fmt` passes `IntDigits` this way, so every `-O3` program needs it.
2. **ARGVAL on x86-64** follows upstream `pass_struct_by_val`: the bytes are
   copied into the outgoing stack arguments (not a private copy passed by
   pointer). CIR gives the adapter no alignment, so it passes 8.
3. **`call-groups/Group`.** Allow count-2 groups whose members differ in type,
   from {5 word, 11, 12 f64, 13 f32}: each member is one eightbyte and goes to
   a register of its own bank, or both go to the stack.
4. **`call-results`.** A `pair(first, second)` spec: rax/rdx for integer
   pieces, xmm0/xmm1 for SSE pieces, in order per bank; pieces are stored at
   offsets 0 and 8 of the result place.
5. **Group alignment 16** affects stack placement only (no even-register rule).
6. **`x64/private-leaf` `context-create`** must not panic; at `-O3` the adapter
   always creates a context.
7. **Jump tables.** The adapter treats an 8-byte data word relocated against an
   *undefined* symbol and read by `mov r64, [rip+slot]` as an address slot (it
   becomes a GOT load). Absolute table entries must point at image-defined
   symbols, or use the relative form.
