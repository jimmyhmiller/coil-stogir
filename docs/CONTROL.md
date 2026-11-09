# Control flow

The graph retains the upstream Sea-of-Nodes control model. Block starts and
terminators are graph nodes; CFG analysis, placement, scheduling, allocation and
edge reconciliation run before target emission. JIT and AOT use the same lowering.

## Integer switches

`builder/switch!(graph, control, selector)` emits SWITCH and ends the current
control chain. The selector must be an integer/address scalar value, not a VAR
storage identity. Case blocks start with these checked builders:

- `case-value!(graph, switch, constant)` matches one value.
- `case-range!(graph, switch, low, high)` matches an inclusive interval.
- `case-default!(graph, switch)` handles values outside the explicit cases.

Endpoints must be numeric constants of exactly the selector type. Signed values
use the type's signed order, including CHAR's signed byte storage. BOOL endpoints
are zero or one. Ranges cannot wrap or reverse; a signed interval from -1 to zero
is valid, while one from the signed maximum to the signed minimum is not.

Builders check local shapes and types before mutation. Complete-dispatch
validation additionally requires exactly one explicit default and disjoint case
intervals. Duplicate values, intersecting ranges, non-case SWITCH successors and
malformed raw nodes are rejected. All case/default exits must participate in the
compilation's observable roots. Omitting a projection is diagnosed rather than
silently producing a branch to an unbound target.

Case blocks may have normal memory operations, calls and further control flow.
Use END nodes to feed a MERGE and PHI nodes for case results. The order of PHI
inputs follows MERGE predecessor order, independent of dispatch sorting. Loop
backedges use the existing LOOP_BEGIN/LOOP_END and loop-phi construction.

## Equality chains

`equality-chain/rewrite!` runs in the SCCP pipeline after the iterative cleanup
has settled (`sccp/finish-compacting!`), followed by one more cleanup when it
changed anything. It finds IF nodes that test `EQ(v, c)` or `NE(v, c)` for one
integer value `v` and a same-typed constant, where the projection taken when
`v != c` is used only by the next such IF. The head IF becomes the SWITCH, each
matching projection its CASE_VAL, the last non-matching projection the
CASE_DEFAULT; the links between them become NOPs. Nothing moves to a new
reference, so MERGE predecessors, PHI inputs and roots are unchanged, and a
projection or IF that is an observable root ends the chain instead of being
removed. A repeated constant ends the chain before the repetition.

Four or more tests always become a SWITCH. Three do when every match reaches
one MERGE through empty blocks and no PHI there needs a per-edge value (one
bit test); two do under the same condition when their constants are adjacent
(one range test). Other short chains, including two-way tag tests with separate
targets, stay IFs.

## AArch64 dispatch

Case intervals are heapsorted in O(n log n) time with bounded extra sorting
storage. Flipping the storage sign bit maps signed values to unsigned order keys
without overflow. Selection normalizes the selector into reserved x16; comparison
constants use x17. Balanced comparisons give O(log n) dispatch depth for sparse
cases and ranges. Default-only dispatch is supported too.

Dispatch branches to a separate stub for each case/default. Each stub reconciles
ordinary live values before entering its block. Comparisons finish before any
edge copy can overwrite a scratch register. The usual parallel-copy machinery
handles GPR/SIMD/spill values and subsequent merged-result phis. Fixed and dynamic
stack storage keep the same anchored-frame semantics as other branches.

Dense singleton switches use the pinned upstream density rule: more than two
cases and `(maximum-minimum) < case-count*8`. Ranges, sparse cases and smaller
switches retain balanced comparisons. The normalized selector subtracts the
minimum and uses one unsigned bounds check, which also rejects values below the
minimum. Holes in the table point to the default edge stub.

Before choosing a strategy, dispatch compares the code addresses behind its
edges: a case block that is forwarded to the default's address is the default
and gets no test. Singleton cases inside one 64-value window that reach at most
three addresses use a bounds check and one mask test per address (`mov x17, #1`,
`lsl x17, x17, key`, `and x16, x17, #mask`, `cbnz x16`), with LLVM's thresholds:
three cases for one address, five for two, six for three. One address that
covers its whole window needs the bounds check alone. This takes precedence
over a table. A closing jump to the default is omitted when the default block
follows the dispatch and no edge needs a stub.

Tables contain signed 32-bit displacements relative to the table base. ADR,
indexed LDRSW, ADD and BR form the destination without an absolute pointer or a
per-entry image relocation. Each table is adjacent to its dispatch sequence, so
ADR has a fixed, checked displacement independent of the function size. The same
patched text works in raw JIT mappings, shared images and linked Mach-O objects.
Signed relative fixups validate every record before writing any entries.

The shared image retains ordered data-in-code ranges. Mach-O serialization emits
LC_DATA_IN_CODE with JUMP_TABLE32 entries, splitting lengths above the u16 limit
at element boundaries. In MH_OBJECT these entries use section VM offsets,
matching LLVM MC, rather than text file offsets. Ordinary functions retain the
previous object layout without an extra command.

Dispatch-strategy measurements and general long-branch relaxation remain
unfinished. These implementation details are not performance claims. Full compiler
integration and LLVM/TPDE comparisons remain delivery gates.

## Trap and unreachable paths

`builder/trap!(graph, control)` emits a void, control-pinned debug breakpoint.
Its successor may continue the control chain. `builder/unreachable!(graph,
control, previous)` emits a void terminal; use zero for an unlinked exit or an
existing terminal reference to extend the optional exit list. Both builders
require an open control chain and reject malformed operands before mutation.

UNREACHABLE has three operand slots: control, a reserved zero word, and the
optional terminal link. The reserved word remains present even though it is not
a graph edge. START's first operand may hold the terminal-list head. Complete
validation checks head/link targets and rejects cycles in linear time, allowing
forward links. Zero-only chains need no color-array allocation. Root marking
follows these links, so either the exit head or a linked START can retain all
observable exits; the links do not create CFG edges or register values.

AArch64 TRAP emits BRK #0. The reference backend marks UNREACHABLE skipped; this
target uses BRK #0 followed by a branch back to that breakpoint. The extra branch
prevents ordinary debugger resumption from falling through into a neighboring
block. These non-returning paths do not run a function epilogue. Returning paths
continue to restore their fixed/dynamic stack frames normally. A caller must
include non-returning exits among its observable roots or retain them through
the terminal list, just as it retains returning exits.

Tests execute ordinary paths directly and isolate trap paths in child processes.
A SIGTRAP handler exits the child with a checked status, avoiding a crash report
or termination of the test runner. JIT and linked AOT checks cover IF paths,
dense/sparse exhaustive-match defaults, never-returning functions and aligned
dynamic frames. These policies do not establish the still-open compiler backend
integration or performance comparisons.
