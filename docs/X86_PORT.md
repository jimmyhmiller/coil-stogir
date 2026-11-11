# x86-64 port

Working design for the x86-64 backend. Everyone working on the port reads this
first. It records decisions; change it in the same commit as the code when a
decision changes.

## Scope and bar

- Target: x86-64 Linux, System V ABI, ELF objects, Linux JIT. macOS x86-64 later.
- Baseline CPU: plain x86-64 (SSE2). No BMI, LZCNT, POPCNT, SSE4.1, AVX or FMA
  unless a function is compiled with an explicit feature option (none exist yet).
  This matches what the LLVM backend it is measured against targets by default.
- Done means the two project goals hold on the Linux host for the compiler
  bootstrap: generation wall time at least 5x faster than parallel LLVM O3, and
  the Stogir-built compiler within 1.10x of the LLVM-built compiler's runtime.
- Correctness, JIT and AOT, and the pinned upstream architecture are preserved.
  The reference for instruction selection and constraints is upstream
  `ir_x86.dasc` (`/Users/jimmyhmiller/Documents/Code/open-source/ir`).
- AArch64/macOS must keep passing unchanged. Neutral code that changes is
  re-tested on the Mac.

## Layout

- `src/stogir/x64/*.coil`, module names `stogir.x64.NAME`, mirroring the `a64`
  file names wherever the same job exists (`compile`, `function`, `match`,
  `select`, `emit`, `constraints`, `allocate`, `call`, `call-abi`, ...).
- `src/stogir/native/compile.coil` (`stogir.native.compile`) and
  `src/stogir/native/private-leaf.coil`: the same public API as
  `stogir.a64.compile` / `stogir.a64.private-leaf`, forwarding to the backend of
  the target being compiled for (`stogir.target/arch-pick`). Embedders and
  target-neutral tests import these. The facade imports only the chosen backend
  (the import itself is inside `arch-pick`), so a backend's signature mismatch
  shows up when compiling for that machine. `object` is built in the facade from
  `image` and `stogir.aot.native`; a backend does not provide it.
- `src/stogir/native/private-types.coil`: the private `Context` / `Publication`
  types and option switches shared by both backends (today a re-export of the
  definitions in `stogir.a64.private-leaf`).
- `src/stogir/jit/native.coil`, `src/stogir/aot/native.coil`: JIT and object
  writing for the target (Mach-O on Darwin, ELF on Linux).
- Logic that is target-neutral but lives under `a64/` today (phi coalescing,
  the parallel-move skeleton, the node walk) is moved to `src/stogir/` and
  shared when an x64 file would otherwise be a copy. Moving is preferred over
  copying; a copy needs a reason written at the top of the file.
  Moved so far: `stogir.phi-coalesce` (was `stogir.a64.phi-coalesce`),
  `stogir.reciprocal` (the magic-number recipes of `stogir.a64.reciprocal`)
  and `stogir.view-coalesce` (the view joining of `stogir.a64.coalesce`;
  each backend's `coalesce` module says which nodes are views).
  The x64 driver, transfers and fixups are written again rather than shared,
  each with its reason at the top of the file (4-byte words, AArch64
  scratches, shrink-wrapping interleaved with the node walk).
- `src/stogir/x64/families.coil` classifies every node into the core or one
  operation family and is the only dispatch to the family modules;
  `docs/X86_FAMILIES.md` describes the extension points.
- `src/stogir/x64/testing.coil` is test support (graph shorthands, a
  reference evaluator, calling generated code); only tests import it.

## Registers

Library register numbers: general registers 0..15 are the hardware numbers
(rax 0, rcx 1, rdx 2, rbx 3, rsp 4, rbp 5, rsi 6, rdi 7, r8..r15); XMM
registers are 32..47.

| Role | Registers |
|---|---|
| Never allocated | rsp, rbp (frame anchor), r10 and r11 (scratch), xmm14 and xmm15 (scratch) |
| Caller-saved, allocatable | rax rcx rdx rsi rdi r8 r9; xmm0..xmm13 |
| Callee-saved, allocatable | rbx r12 r13 r14 r15 |
| Integer arguments | rdi rsi rdx rcx r8 r9 |
| Float arguments | xmm0..xmm7 |
| Results | rax, rdx; xmm0, xmm1 |
| Indirect call target, tail-call target | r11 |
| Parallel-move cycle holder | r11, xmm15 |

Two scratch registers per bank mirror a64's x16/x17 and v30/v31 so emitters
keep the same shape. Freeing rbp and one scratch for allocation is a later
tuning step, not part of the first correct version.

Scratch roles: r10 carries an emitter's first operand when it is a constant
or a reload, and is the data scratch of memory-to-memory transfers; r11
carries the second operand and is the cycle holder (xmm14 and xmm15
likewise). Nothing lives in a scratch between two nodes.

## Integer values in registers

A value of type T is defined in the low `8 * size(T)` bits of its register;
every higher bit is unspecified, also for 32-bit values, for parameters and
after a spill and reload. BOOL is a byte holding 0 or 1. Low-bit arithmetic
(ADD SUB MUL AND OR XOR NOT NEG SHL, moves, cmovcc) runs at 32 bits for every
type of at most four bytes and at 64 bits otherwise; operations that read the
high bits (compares, SHR, SAR, rotates, the truth test) use the 8- and 16-bit
instruction forms at the type's own width; DIV and MOD extend narrow operands
to 32 bits. A returned value is extended to 32 bits by its signedness. The
rule is written out at the top of `x64/value.coil`.

Views. Because the bits above a value's width are unspecified, the low part
of a wider value is already a valid narrower one: COPY, a same-size integer
BITCAST and every integer TRUNC are *views*. They are emitted as nothing when
source and result share a register and otherwise as a move of the whole
64-bit register, and `x64/coalesce.coil` joins each with its source into one
allocation group (`stogir.view-coalesce`). The whole-register move matters:
a narrow view can share its group with a 64-bit value that lives on, so a
move at the view's own width would cut that value. A conversion to BOOL is
not a view (it canonicalizes to 0 or 1), nor is SEXT or ZEXT.

Results the IR leaves undefined, chosen to match the AArch64 backend:
CTLZ(0) is the type's width; CTTZ(0) is 64 for 64-bit types and 32 for
every narrower type; ABS of the minimum is the minimum.

## What x86 needs that a64 did not

1. **Two-address instructions.** `op rd, rm` overwrites rd. The emitter
   produces `mov rd, rn; op rd, rm`; when rd = rm it commutes the operation if
   it can, and otherwise goes through r11. The definition gets a `Part.hint`
   to its first operand so the move usually disappears.
2. **Fixed registers.** Expressed with `allocation/reserve!` clobbers and
   advisory preferences, not with fixed uses. A kind-2 fixed *use* (at the
   even operand position) cannot always be allocated: when the operand lives
   on past the instruction and its fixed register is already promised from
   the definition position (the result's coalesced PHI group holds it across
   a lifetime hole), the operand would have to change register at an odd
   position, which only calls lower, and the allocator reports "eviction did
   not make a register available". The differential stress test hit this
   about once in 30 000 functions with a fixed rcx count. Kind-2 fixed
   *definitions* remain fine (register parameters, later call results).
   - Variable shifts and rotates: rcx is clobbered over the operand position
     `[2i, 2i+1)`, so no operand and no live value is in it; the emitter copies
     the count into ecx (masking it for 8- and 16-bit values, whose hardware
     count is taken modulo 32). The result may be rcx; the emitter then
     shifts in a scratch register.
   - `div`/`idiv`: rax and rdx are clobbered over `[2i, 2i+1)`; the register
     that does not hold the result stays clobbered over `[2i+1, 2i+2)`; the
     result prefers rax (DIV) or rdx (MOD) and is moved when it landed
     elsewhere. The dividend is copied into rax, a constant divisor into r11.
     Division by zero and the overflowing signed quotient trap (#DE); the IR
     leaves both undefined and nothing is checked. AArch64 hardware returns
     0 / the dividend / the minimum for those inputs, and
     `tests/jit-division.coil` checks exactly those results on AArch64 and,
     on x86-64, that the same inputs die with SIGFPE. Trapping matches what
     an LLVM-built program does on x86-64. Division by a constant other
     than 0, 1 and -1 uses no `div` (`x64/reciprocal.coil`: shifts for
     powers of two of either sign, multiply-high otherwise); 0, 1 and -1
     keep the hardware division and with it the trap.
   - One-operand `mul`/`imul` follow the same pattern (clobber, copy in,
     prefer): unsigned 64-bit MUL_OV (`x64/checked.coil`) and the 64-bit
     multiply-high of division by a constant (`x64/reciprocal.coil`).
     `cmpxchg` (atomics, not written yet) will too.
3. **Flags.** Almost every ALU instruction writes flags. Rules:
   - Moves emitted between any two nodes (spills, reloads, phi moves, constant
     and address materialization) never write flags: `mov`, `lea`, `movaps`,
     `mov r, imm`. `xor r, r` zeroing is used only by emitters that know no
     flag value is live across it.
   - A compare is emitted directly before its consumer (`jcc`, `setcc`,
     `cmovcc`), as a64 already repeats compares per user. Every operand load
     and constant comes before the compare; after it only `mov` (COND arms,
     edge moves, `movzx` after `setcc`) is emitted.
   - No flag value is live between two nodes, so a node's own code may use
     any instruction once its last flag consumer is emitted (DIV zeroes edx
     with `xor`). The one exception: a checked producer (ADD_OV, SUB_OV,
     MUL_OV) leaves its overflow condition in the flags for the OVERFLOW
     projection, which the schedule keeps directly behind it
     (`stogir.checked-schedule`); only allocator transfers, which are moves,
     can sit between the two (`x64/checked.coil`, as NZCV on AArch64).
   - Floating compares use `ucomiss/ucomisd` and handle the parity flag for
     unordered operands exactly as upstream's `ir_emit_cmp_fp` does
     (`x64/fcompare.coil`): each predicate picks the operand order whose one
     condition code is right for unordered operands, and only EQ and NE need
     parity too. A condition handed to a flag consumer is therefore an
     *extended condition*: a condition code, or a code "and not parity" / "or
     parity". IF takes two branches for those (`edges/branch-edge-parity!`),
     a BOOL two `setcc`, an integer COND two `cmovcc`.
   - SSE instructions other than the compares never write EFLAGS, so `xorps`
     zeroing, `movaps`/`movss`/`movsd`, `andps`, `pcmpeqd` and the like may
     sit between a flag producer and its consumer, unlike `xor r, r`.
4. **Variable-length code.** Offsets are bytes. A branch is emitted as rel32
   with a fixup record; shrinking to rel8 and loop alignment are a separate
   pass over records, not word arithmetic. There are no veneers in text.
   A record (`x64/fixups.coil`) holds the instruction's first byte, its
   displacement field, its label and its condition; labels are a table of
   byte offsets. Neither the relaxation pass nor alignment padding exists
   yet: the block layout's alignment requests are ignored.
5. **Memory operands and LEA.** Loads fold into ALU and compare operands, and
   `lea` covers add-with-shift and three-operand adds, following upstream's
   fusion rules. This is selection work on top of a correct register-only
   version, not a prerequisite for it. The register-only address forms
   exist (`x64/lea.coil`, RULE-LEA): sums of a base, a scaled index and a
   displacement, multiplication by 2, 3, 5 and 9, and by other powers of two
   as a shift; an address form absorbs a single-use producer of its block.
   Folding loads is the memory family's.

## Floating point

Scalar f32/f64 live in the low bytes of XMM registers (`x64/floating.coil`;
operand helpers in `x64/value.coil`, "Floating values").

- **Constants.** +0.0 is `xorps x, x`, anywhere (it writes no flags). Every
  other constant is loaded from a per-function constant pool with
  `movss/movsd x, [rip + disp32]`, or read from it directly as the memory
  operand of an arithmetic or compare instruction, as compilers do. The pool
  is appended to the function's own text after its last instruction
  (`x64/pool.coil`: 8-byte entries, then 4-byte ones, identical bit patterns
  shared, padded to 8 bytes, recorded as a text data range), so the
  displacement is fixed when the function is finished and no image
  relocation or data symbol is involved. While the function is emitted a
  load carries a `code/Reference` (kind PC32, addend -4, target the
  constant's graph reference), which `pool/finish!` resolves and removes.
  Constants the emitters need themselves (sign masks, 2^52, 2^63, one half)
  are built without memory: `pcmpeqd` + shift, or `mov r10, imm` + `movq`.
  A floating PHI constant bound for a spill slot is stored through r10.
- **Two-address arithmetic.** `rd = left OP right` is `movaps rd, left;
  op rd, right`, the right operand read from its register, its spill slot or
  the pool. When rd is the right operand's register ADD and MUL commute and
  SUB and DIV go through xmm14.
- **NaNs.** Arithmetic follows the hardware: a NaN operand is returned
  quieted (the first operand of the instruction when both are NaNs, so the
  commuted forms make the choice between two different NaNs unspecified, as
  it is for constant folding), and an invalid operation gives the x86
  default NaN, whose sign bit is set (AArch64's is clear). The selecting
  MIN/MAX and FMIN/FMAX/FMINNM/FMAXNM give the AArch64 backend's results bit
  for bit, NaNs and signed zeros included; so do NEG, ABS and the roundings.
- **No conditional move for XMM.** Floating COND and the selecting MIN/MAX
  are a compare and a short forward branch over a `movaps`. Jumps inside one
  node are rel8 and patched locally (`x64/local.coil`); they never span a
  fixup record, so branch relaxation cannot move anything between them.
- **SSE2 only.** ROUND_EVEN/UP/DOWN/ZERO/AWAY are exact inline sequences
  (no `roundsd`): magnitudes of 2^52 (2^23) and above are returned as they
  are, smaller ones go through `cvttsd2si`/`cvtsi2sd` or the add-and-subtract
  2^52 identity and keep the operand's sign. They assume MXCSR's default
  round-to-nearest mode, like every other arithmetic instruction. FMA has no
  baseline instruction and is rejected with a clear error until the call
  family can call libm's `fma`/`fmaf` from inside a node (which also needs an
  image, not bare text).
- **Conversions.** INT2FP is exact for every integer type (u64 with the top
  bit set is halved with a sticky low bit and the result doubled). FP2INT is
  `cvttss2si/cvttsd2si`; u64 results add a second conversion of `x - 2^63`.
  The IR leaves NaN and out-of-range inputs undefined (constant folding
  folds none of them): AArch64 saturates there, x86-64 returns what the
  instruction gives. Every defined input agrees with constant folding.
- **Memory.** `families/of` routes LOAD/STORE and VAR/VLOAD/VSTORE of a
  floating type to the floating family (`x64/float-memory.coil`: one base
  register, no displacement folding) until the memory and locals families
  handle every type; those accesses should then go through the memory
  family's address-mode selection.
- **Parameters and results.** xmm0..xmm7, then 8-byte stack slots; a result
  in xmm0. The driver emits floating PARAM, RETURN and IF itself.

## Frame

The a64 frame model is kept: logical offsets measured upward from rsp after
the prologue (outgoing area, result slot, locals and static allocas, spills,
callee-saved area). Differences:

- The return address is on the stack at entry (`[rsp]`), so stack parameters
  start at entry rsp + 8 and there is no link register or link slot.
- Prologue: `sub rsp, N` and callee-saved registers stored with `mov` into the
  callee-saved area (so shrink-wrapping and the offset model carry over).
  `push rbp; mov rbp, rsp` first when the frame is anchored (dynamic stack or
  over-alignment); rbp is then the base for locals and parameters.
- rsp is 16-byte aligned at every call: entry rsp + 8 + N is a multiple of 16.
  N is the frame contents rounded up to 8 modulo 16; a function without
  frame contents (no spill, no preserved register, no frame object) has
  N = 0 and no prologue.
- Frameless leaves may use the 128-byte red zone for spills. Not done yet:
  a function with any spill gets a frame.
- Traps are `ud2`.
- Not in the first version: anchored (rbp) frames, shrink-wrapping,
  spill-home planning. The allocator runs with the pinned plain tuning.

## Calls (System V)

- The Coil compiler's CIR arrives already classified into eightbytes, so the
  library's job is placement: integer and SSE eightbytes take the next free
  register of their bank; a group that does not fit goes to the stack whole
  and does **not** exhaust the bank; stack slots are 8 bytes (16-byte alignment
  for 16-byte-aligned values).
- Indirect result: hidden pointer in rdi, returned in rax.
- Register results: rax/rdx and xmm0/xmm1, including mixed pairs (one integer
  and one SSE eightbyte). `call-results/Spec` is extended for mixed pieces.
- Variadic calls pass unnamed arguments in registers like named ones and set
  `al` to the number of vector registers used.
- Narrow integer arguments are extended by the caller to 32 bits; a callee
  never trusts the upper bits of a narrow parameter.
- Calling-convention number in `Prototype.flags`: 0 (default) and 8 (System V)
  are accepted on x86-64.
- Named functions are called with `call rel32` (PLT32); named data and function
  addresses are loaded from a private 8-byte slot with `mov r, [rip+slot]`
  (PC32); strings and constants are addressed with `lea r, [rip+x]` (PC32).
- Private leaf calls: the written-register set of a leaf is recorded while it
  is emitted (no decoder).

## Image and relocations

`image.Image` carries a machine (1 AArch64, 2 x86-64). Relocation kinds:
1 ABS64 (both), 2..4 AArch64 only, 5 PC32 and 6 PLT32 (x86-64 only, explicit
addends; the field is the last 4 bytes of the instruction unless an immediate
follows, in which case the addend accounts for it).

## Testing

- `tools/x86/remote-test.sh tests/NAME.coil ...` runs tests on the Linux host.
- Target-neutral tests import `stogir.native.compile` and `stogir.jit.native`
  and must pass on both hosts. A test ported from `stogir.a64.compile` keeps
  its name; the port is a change of imports plus platform symbol names
  (`stogir.target` helper), never a weakening of what it checks.
- Tests of x64 internals are named `x64-*.coil`.
- `tests/X64_STATUS.md` lists every test with its category and, for facade
  tests, its operation family; `tools/x86/family-tests.sh FAMILY` prints a
  family's tests. A facade test may keep an AArch64 instruction-shape check as
  `(target/arch-pick CHECK (do))`; object symbols are written
  `(target/os-pick "_name" "name")`.
- Every new behavior has a test; every stub is a hard error with a clear
  message.

## Optimization levels

As on AArch64: level 0 is rejected, level 1 generates the graph as given,
levels 2 and 3 run SCCP first. The level-3 stages of the a64 path
(global-load forwarding, fact folding, select diamonds, loop-load hoisting,
rotation, loop strength reduction, the vectorizer) are not run on x86-64
yet (`LEVEL-THREE-CHAIN` in `x64/compile.coil`): the strength stage uses an
AArch64 cost module and the vectorizer produces vector operations no family
emits. Level 3 generates what level 2 does. `a64.constant-hoist` and
`a64.return-values` are not run either.

## Phases

0. Encoder; neutral image/link/relocate/JIT/ELF layers; Linux measurement tools.
1. Core: a function of integer values, parameters, constants, compares,
   branches, loops and PHIs compiles and runs through the facade; the driver
   has one hook module per operation family. (Done on branch `x86/core`,
   tested directly against `stogir.x64.compile`; see `docs/X86_FAMILIES.md`.)
2. Families in parallel: integer completeness; memory and stack; calls and ABI;
   floating point; vectors; switches, branch relaxation and peepholes.
3. Coil adapter for x86-64, compiler builds itself with Stogir on Linux, FAST
   and bootstrap reproduce.
4. Tuning rounds against the two goals.
