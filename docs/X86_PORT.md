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

## What x86 needs that a64 did not

1. **Two-address instructions.** `op rd, rm` overwrites rd. The emitter
   produces `mov rd, rn; op rd, rm`; when rd = rm it commutes the operation if
   it can, and otherwise goes through r11. The definition gets a `Part.hint`
   to its first operand so the move usually disappears.
2. **Fixed registers.** Expressed with the existing vocabulary: a kind-2 fixed
   use for the operand, a kind-2 fixed definition, and `allocation/reserve!`
   for clobbers.
   - Variable shifts and rotates: count fixed in rcx at the use position; rcx
     reserved over the definition position so the result cannot land in it.
   - `div`/`idiv`, one-operand `mul`/`imul` (64-bit high halves, unsigned
     checked multiply, reciprocal division of 64-bit values): rax and rdx fixed
     or reserved as upstream's `ir_get_target_constraints` does.
   - `cmpxchg`: rax.
3. **Flags.** Almost every ALU instruction writes flags. Rules:
   - Moves emitted between any two nodes (spills, reloads, phi moves, constant
     and address materialization) never write flags: `mov`, `lea`, `movaps`,
     `mov r, imm`. `xor r, r` zeroing is used only by emitters that know no
     flag value is live across it.
   - A compare is emitted directly before its consumer (`jcc`, `setcc`,
     `cmovcc`), as a64 already repeats compares per user.
   - Floating compares use `ucomiss/ucomisd` and handle the parity flag for
     unordered operands exactly as upstream's `ir_emit_cmp_fp` does.
4. **Variable-length code.** Offsets are bytes. A branch is emitted as rel32
   with a fixup record; shrinking to rel8 and loop alignment are a separate
   pass over records, not word arithmetic. There are no veneers in text.
5. **Memory operands and LEA.** Loads fold into ALU and compare operands, and
   `lea` covers add-with-shift and three-operand adds, following upstream's
   fusion rules. This is selection work on top of a correct register-only
   version, not a prerequisite for it.

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
- Frameless leaves may use the 128-byte red zone for spills.
- Traps are `ud2`.

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

## Phases

0. Encoder; neutral image/link/relocate/JIT/ELF layers; Linux measurement tools.
1. Core: a function of integer values, parameters, constants, compares,
   branches, loops and PHIs compiles and runs through the facade; the driver
   has one hook module per operation family.
2. Families in parallel: integer completeness; memory and stack; calls and ABI;
   floating point; vectors; switches, branch relaxation and peepholes.
3. Coil adapter for x86-64, compiler builds itself with Stogir on Linux, FAST
   and bootstrap reproduce.
4. Tuning rounds against the two goals.
