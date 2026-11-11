# x86-64 operation families

How to add an operation family to the x86-64 backend without touching the
core or another family's files. Read `docs/X86_PORT.md` first for the design
decisions; this document is the map of extension points.

## What exists

The core (`src/stogir/x64/`) compiles integer functions end to end: PARAM,
constants, COPY, ADD SUB MUL DIV MOD, AND OR XOR NOT NEG, shifts and rotates,
integer comparisons, IF, COND, SEXT ZEXT TRUNC and integer BITCAST, PHI, loops,
MERGE, RETURN, TRAP and UNREACHABLE, with spilling, preserved registers and a
fixed frame. Everything else belongs to a family, and each family is a module
whose entry points currently return a clear `Err`.

| Family constant | Module(s) | Operations |
|---|---|---|
| `MEMORY` | `x64/memory.coil` | LOAD, STORE, RLOAD, RSTORE, TLS_ADDR; named constants (FUNC, SYM, STR) as operands |
| `LOCALS` | `x64/locals.coil` | VAR, VADDR, VLOAD, VSTORE |
| `STACK` | `x64/stack.coil` | ALLOCA, AFREE, BLOCK_BEGIN, BLOCK_END, FRAME_ADDR |
| `CALL` | `x64/call.coil`, `x64/call-abi.coil` | CALL, TAILCALL, ARGVAL, PROTO, EXITCALL, VA_* |
| `FLOATING` | `x64/floating.coil` | every node of FLOAT/DOUBLE type or reading one |
| `VECTOR` | `x64/vector.coil` | every node of a vector type or reading one |
| `ATOMIC` | `x64/atomic.coil` | ATOMIC_LOAD/STORE/RMW/CMPXCHG/FENCE |
| `CHECKED` | `x64/checked.coil` | ADD_OV, SUB_OV, MUL_OV, OVERFLOW |
| `SWITCH` | `x64/switch.coil` | SWITCH (the CASE_* projections are block starts) |
| `BITS` | `x64/bits.coil` | integer ABS, BSWAP, CTPOP, CTLZ, CTTZ, MIN, MAX |
| (rule hook) | `x64/reciprocal.coil` | DIV/MOD by a constant without `div` |

Each placeholder module's header lists its operations, the interface it must
implement and the notes specific to it.

## Where the dispatch is

`x64/families.coil` is the only module that names the families.

- `families/of graph reference` classifies a scheduled node (by opcode, by its
  type, and by the types of its data operands: a comparison of two doubles
  is `FLOATING` although its own type is BOOL; an ADD of a symbol address is
  `MEMORY`). The matcher calls it once per node and stores the answer in
  `Plan.families`; later stages read `plan/family`.
- `families/select!`, `families/constrain!`, `families/emit!` forward to the
  family's module.

The three stages call into it at exactly one place each:

| Stage | File | Call |
|---|---|---|
| matching | `x64/match.coil`, `build-fusing`, "Tiles, and the families' own selection" | `families/select!` (and `switch/select!`) |
| constraints | `x64/constraints.coil`, `build-matched` | `families/constrain!` (and `switch/constrain!`) |
| emission | `x64/function.coil`, `body-ordered`, the node `cond` | `families/emit!` (and `switch/emit!`, `reciprocal/emit!`) |

To move an opcode into a family, or to make a family claim a new shape,
change `families/of` only.

## The three entry points

```lisp
(defn select! [(state (mut plan/Matching)) (graph g/Graph) (reference i32)]
  (-> (Result i32 (slice u8))))
(defn constrain! [(set (mut uses/Set)) (graph g/Graph) (matched plan/Plan)
                  (reference i32) (position i64)] (-> (Result i32 (slice u8))))
(defn emit! [(out (mut code/Buffer)) (cx context/Context) (reference i32) (position i64)]
  (-> (Result i32 (slice u8))))
```

### `select!` — matching (before liveness)

Called once per scheduled node of the family, in schedule order, with the
tables of `plan/Matching` (`x64/plan.coil`) complete for `blocks`, `counts`
and `protected`, and `tiles` filled for the nodes scheduled before it.

- Record what the emitter will need: a `select/Tile` in `tiles[reference]`
  (add rule constants to `x64/select.coil`; rule numbers 100..119 are
  reserved for the reciprocal family, take a fresh range for yours), or
  entries in the family's side tables (`addresses`, `offsets`, `indices`,
  `index-shifts` for memory; add a table to `plan/Plan` and `plan/Matching`
  when yours needs one).
- To absorb a producer (fold a load into an operand, a shift into an address):
  set `omitted[producer]` and lower `counts`. An omitted node emits nothing
  and defines no register; its consumer must then read the producer's inputs.
  The neutral `stogir.matched-uses` builds the machine inputs: the core
  passes `comparisons` as its redirect table (a consumer takes its redirect's
  inputs); `match.coil` patches input ranges after the build for anything the
  redirect cannot express (see how a fused COND gets its arms back). Do the
  same for your node.
- Return `Ok` for nodes that need no selection.

### `constrain!` — register requirements

Called once per scheduled node of the family that is neither omitted nor
rematerialized. `position` is `2 * schedule index`: operands are read at
`position`, the result is defined at `position + 1`. Everything goes through
`x64/uses.coil`:

| Need | Call |
|---|---|
| operand in a register | `uses/use!` |
| operand anywhere (register or spill slot) | `uses/use-anywhere!` |
| result in a register | `uses/define!` |
| result in one fixed register (a call result in rax) | `uses/define-fixed!` |
| an instruction overwrites a register | `uses/clobber! set register start end` |
| result would like operand 1's register (two-address) | `uses/hint!` |
| value would like one register | `uses/prefer!` |
| a frame object | push a `uses/Local` on `(.locals set)` |
| outgoing call area | raise `(.outgoing-size set)` (multiple of 16) |
| a fixed register that is the instruction's own result | `uses/define-fixed!` plus `uses/clobber-unless-live!` (the clobber applies only when the result is dead) |
| the function executes a call instruction | set `(.calls set)` (forces a frame so rsp is aligned) |
| allocator transfers at a definition position that the emitter lowers itself | push `position + 1` on `(.definition-moves set)` |

Do **not** use `uses/use-fixed!` for an operand that may live on after the
instruction (see "Fixed registers" in `docs/X86_PORT.md`): clobber the
register over `[position, position + 1)` and copy the operand in. A clobber
that starts at `position` keeps operands and live values out of the
register; one that starts at `position + 1` keeps live values and the result
out.

`x64/allocate.coil` consumes the whole `Set`; a family never edits it.

### `emit!` — machine code

Appends the node's code to `out`. `cx` (`x64/context.coil`) gives the graph,
the location view, the frame base, the plan, the frame and the frame size.

- Operands: `emit/operand! out cx reference position scratch` returns the
  register holding an integer operand (a constant or spilled value is moved
  into `scratch` with `mov`); `emit/into!` copies it into a chosen register;
  `emit/destination cx reference position` is the result's register.
  `value/register-of` peeks without emitting.
- Scratch registers: r10, r11, xmm14, xmm15 are free inside one node and hold
  nothing between nodes.
- Encoders: `x64/encode.coil`; feed each result through `code/accept!`.
- Flags: nothing is live on entry or exit. Inside the node only `mov`, `lea`
  and SSE moves may sit between a flag producer and its consumer.
  `emit/flags!` (integer compare tile) and `truth/flags!` (value is nonzero)
  load every operand first and return the condition code.
- Narrow integers: bits above the type's width are unspecified
  (`x64/value.coil`, header). Extend before any instruction that reads them.
- Frame objects: `(get (.locals (.frame cx)) owner)` is the logical offset;
  `frame-address/slot (.base cx) offset` its memory operand. Stack parameters
  are at `[rsp + frame-size + 8 + offset]`.
- References to named symbols: push a `code/Reference` (kind PC32 or PLT32,
  explicit addend) and resolve it in `x64/image.coil` `finish!`, which today
  rejects any reference.

### Families with a different shape

- **SWITCH** (`x64/switch.coil`): `emit!` also receives the control-flow
  state, because it branches: `edges/Flow`, `(mut edges/Control)`, the
  fall-through successor `next`. Branch with `edges/branch-edge!` (it emits
  the edge's moves in a stub when there are any) and `fixups/jump!`; jump
  tables are `fixups/Relative` words.
- **Reciprocal division** (`x64/reciprocal.coil`): not a node family but a
  rule hook. `reciprocal/select` may replace the `RULE-DIVIDE` tile of a DIV
  or MOD; its rules are then constrained and emitted by
  `reciprocal/constrain!` and `reciprocal/emit!`.
- **Calls** (`x64/call.coil`, implemented): placement is
  `x64/abi-arguments.coil` (shared with `x64/incoming.coil`) and
  `x64/call-abi.coil` (one call's layout). The matcher asks
  `call/select-tails!` once per function for the tail-call plan
  (`plan/tail-mode`). `call/constrain!` announces `position + 1` in
  `(.definition-moves set)`; the driver then does not emit the allocator's
  transfers at that position but hands them to `call/emit-call!`
  (`function.coil`, `call-node!`), which also covers TAILCALL. PROTO and
  ARGVAL go through the ordinary `emit!`. Private-leaf contexts reach the
  family through `(.private set)`.
- **Registers an emitter may write**: its allocated destination, the
  scratches, and registers it declared with `uses/clobber!`. The driver
  records exactly those as the function's write set for private-leaf callers;
  an emitter that writes anything else must call `code/wrote!`, and one that
  emits a call or jump out of the function `code/called!`.
- **Stack** needs anchored frames: `allocate.coil` rejects
  `(.anchored set)` and alignments above 16, and `function.coil`'s
  `prologue!`/`epilogue!` only know the rsp base.
- **Floating/vector** registers already allocate (the bridge switches to the
  48-register domain when a value of those types is live) and move
  (`x64/transfers.coil`); constants, parameters (`incoming.coil` places them,
  kind 2), returns and PHI constants of those types report a clear error at
  the place to extend.

## Tests

Tests are `tests/x64-NAME.coil`, run on the Linux host with
`tools/x86/remote-test.sh tests/x64-NAME.coil`. `src/stogir/x64/testing.coil`
is the shared support: graph shorthands, an independent reference evaluator
for integer operations, `compiled` / `expect!` / `invoke` (every function is
called through one twelve-argument signature), `dirty` (garbage above a
narrow argument) and a tally.

For a new family, follow the core's pattern:

- a matrix test over types, operand forms (register, constant, repeated) and
  edge values (`tests/x64-core-arithmetic.coil`);
- an emitter test under hand-made register assignments for every aliasing
  and fixed-register case (`tests/x64-core-emit.coil`);
- the operation under register pressure and across loops
  (`tests/x64-core-pressure.coil`);
- extend the generator of `tests/x64-core-stress.coil` with the family's
  nodes once they can be evaluated by the test's interpreter: it found the
  allocator limitation behind the fixed-register rule within 60 000 cases
  when the hand-written tests had not;
- flip the family's case in `tests/x64-core-entry.coil` from "reports not
  implemented" to a real check.

A change to anything outside `src/stogir/x64/` is re-tested on the Mac
(`docs/X86_PORT.md`, "Testing").
