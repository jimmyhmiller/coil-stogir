# Declared call effects

A CALL's prototype may carry one of two effect bits, with the values of pinned
`ir.h`: CONST_FUNC (32) and PURE_FUNC (64). `src/stogir/call-effects.coil` is
the only reader. To this library both bits promise exactly one thing:

> the native target of the call writes no memory its caller can observe.

Nothing else follows from either bit. In particular the library does **not**
assume that

- the result is independent of memory. A PURE target (`memcmp`, `strlen`) reads
  through its pointer arguments, so its result changes when a store changes
  those bytes;
- two calls with equal arguments return equal results, or that a call can be
  moved, merged, hoisted out of a loop or deleted. A CALL is a control-chain
  instruction whatever its prototype says and stays where the frontend put it,
  in order with every STORE and every other CALL;
- the call returns, or does not trap.

What the promise is used for is the opposite direction only: a query that walks
the control chain backwards from a LOAD, looking for the instruction that last
wrote the loaded bytes, may step over the CALL. Those walks are
`load-forward.coil` (store-to-load and load-to-load forwarding, dead-store
barriers), `global-load-forward.coil`, `copy-forward.coil` and `entry-load.coil`
(reuse across joins and reading a loop-header LOAD once per loop entry). A load
of a location that only declared calls separate from an earlier read of the same
location is therefore the earlier value, and a location a loop only reads and
passes to declared calls is read once before the loop. A STORE between them is
judged by the ordinary alias rules and is unaffected by the calls around it.

## What qualifies

`declared-result` accepts the promise only from a well-formed prototype whose
result type and argument count match the CALL (`calls/signature`); an absent,
malformed or mismatched prototype promises nothing. Three levels follow:

| query | holds for |
| --- | --- |
| `preserves-memory?` | scalar or void result (role 0): the calling sequence itself writes nothing |
| `preserves-address?` | additionally a register-returned aggregate (role 1) whose capture place is provably disjoint from the queried bytes |
| `target-readonly?` | roles 0 and 1, for callers that account for the capture write themselves |

An indirect (x8) aggregate result is always a barrier: the callee writes the
caller's result place.

## Who may set the bits

The frontend, for a target it knows: the Coil adapter sets PURE_FUNC on direct
calls of the hosted C routines `memcmp`, `bcmp`, `memchr`, `strlen`, `strcmp`
and `strncmp`, and only when the callee is an undefined external symbol of
exactly that name called with the routine's own argument count. And the
library, for a body it has verified: `load-forward/nonwriting-verified-body?`
and `call-effects/register-result-body-readonly?` prove a definition
non-writing and the module annotates its direct callers. The inliner ignores
both bits when comparing a call site with a definition
(`call-inline.coil`), so an annotation never blocks inlining, and a CALL that
arrives in a caller by inlining keeps the prototype it was built with.

## Tests

`tests/entry-load.coil` modes 3, 14, 16 and 17: a loop whose header reads its
bound from memory and whose body calls a function. With an undeclared callee
the read stays in the loop (and the callee really does write the bound); with a
PURE_FUNC callee the read moves in front of the loop; with a PURE_FUNC callee
followed by a store through a possibly-aliasing pointer it stays, and the
natively executed result shows the store taking effect. The Coil compiler's
`tests/backend/stogir-readonly-library-calls.coil` runs the same shapes through
real `memcmp`.
