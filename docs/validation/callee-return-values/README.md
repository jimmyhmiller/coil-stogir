# Callee GP return SSA: native checkpoint

Library stage now connects private result-memory promotion to matched RETURN
uses before liveness, intervals and constraints. Complete GP groups remove the
implicit result-slot allocation. Existing typed parallel transfers handle swaps,
shared sources and spills; constant/address recipes follow physical copies.
Return nodes and public C ABI remain unchanged. Raw Buffer relocations retain
validated original constant IDs after the temporary lowered graph is released.

All tests use b27ffeb4 host, LLVM O1, --no-debug --debug-checks --sanitize=address,
COIL_LIBRARY_STATE=0. Instrumentation is on harness/library/C code, not generated
native instructions. Existing aggregate suite plus18preparation policies passes:
10supported direct/join/loop/foreign-write/one-piece/multiple-exit/shared/constant/
symbolic shapes execute240aggregate GP JIT answers and160scalar SSA probes.
Eight partial/escaped/observed/raw-stack/unsupported shapes keep the old path.
The source instruction cells are checked unchanged after each attempt.

Ten Mach-O objects link to driver.c for20ordinary+ASAN C executions/480answers,
including a named llabs function address returned as a word. Identity pair native
object is exactly one RET (4bytes); symbolic return object is ADRP/LDR/RET and
has no SP traffic. Five additional suites pass: module-execution, jit-call,
jit-result-projections (120pressure answers), jit-sccp-control and static-stack.
Disassemblies and transcripts are archived here. Existing aggregate tests cover
stack arguments, nested calls, signed/exact bits, HFA/HVA/x8 and alignment.

Initial integration rejected the void RETURN's ordinary zero input placeholder;
installation now accepts only that placeholder before adding typed return uses.
Allocator recognition also rejects a zero placeholder as an actual GP piece.
Those failures were corrected before the passing results above. No compiler
integration or performance result is claimed by this library checkpoint.

## Advisory result preferences

The first compiler experiment removed Graph.operand's SP traffic but left a
three-move payload/tag swap. Direct return pieces now get advisory GP0/GP1 hints
through existing allocation preferences, with first-hint-wins for shared owners.
The full aggregate/probe/JIT/C matrix passes again, as do module execution,
120projection pressure answers and static-stack under debug/ASAN. No native
compiler performance result is claimed until measured. Identity stays one RET.
