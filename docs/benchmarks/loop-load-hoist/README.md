# Must-execute loop load hoisting

Runtime-first experiment `85f5b70`, based on `b8ec8a6` (induction ranges). The option is
`COIL_STOGIR_HOIST_LOADS=1`; it remains off by default. The existing induction,
inline, allocation and prediction policy is unchanged.

## Transformation and proof

A natural loop must have one external END and at least one backedge. The union
of all backedge predecessor regions must be dominated by the header. Every
scheduled control in that region must be an ordinary LOAD or structural
control. Calls, stores, volatile/atomic operations, guards, stack lifetime
operations and assembly decline the loop; there is no alias heuristic.

Only a leading, sequential header load chain can move. Every address must be
available at the external entry, or formed by floating expressions of values
available there and earlier selected loads. PHIs inside the loop stay variant.
Unique control successors prove that the first read already executes on every
header visit, including the first. Reads retain their original order; an
intervening ineligible control stops the prefix.

The load chain is inserted before the entry END, after its original control
predecessor. Its former control consumers are redirected to the header; data
references and PHI slots are unchanged. The header is retained as an additional
root to preserve the original loop control closure even for a data-only root.
The input graph is immutable. Each edit rebuilds and verifies the complete
analyses, including final verification before returning.

Hoisting runs before rotation to avoid duplicating invariant reads into the
latch. After a successful rotation it runs again: a body load can then move to
the guarded entry, but cannot escape the zero-trip guard. No speculative loads
are introduced. No verifier is removed or bypassed.

## Focused validation

`tests/loop-load-hoist.coil` checks moved-load counts, source immutability,
fixed points, and control-root preservation. It covers invariant and variant
addresses, dependent pointer loads, floating address expressions, body-only
loads, volatile reads, aliasing stores, calls, atomic fences, multiple backedges with an effect
on only one backedge, and hoisting through nested loops. A separate rotation
check requires the moved body load to remain controlled by the entry guard.

Native JIT executions compare hoisting on/off and rotation on/off for zero,
one and many iterations. Loaded values contribute to the returned sum. A loop
with an aliasing store checks both the changing loaded values and final memory.
The zero-trip body-load case passes a null pointer, detecting accidental
speculation. Structural preparation and native emission use debug checks.

## Matched runtime results

Fixed workload root: Coil `stogir-branch-fusion` at `892641a2`; its `src/`
tree is unchanged from `d1efe960`. Each comparison alternates four hosts for
three rounds. All 24 resulting objects have the exact seed SHA256
`9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`.
Raw rows are in `ab1.json` and `ab2.json`; derived ratios are in
`runtime-summary.json`. Values below are billions of cycles, minimum / median.

| Host | Round 1 | Round 2 |
|---|---:|---:|
| LLVM | 42.415 / 42.457 | 42.792 / 43.014 |
| Induction baseline | 53.876 / 54.027 | 54.450 / 54.874 |
| Hoisting | 53.883 / 54.035 | 54.273 / 55.016 |
| Hoisting + rotation | 54.619 / 55.249 | 55.397 / 56.524 |

Hoisting changes cycles by +0.014% / +0.015% in the first comparison and
−0.326% / +0.259% in the second. This is not a demonstrated runtime gain.
Rotation is worse in both comparisons: +1.38% / +2.26% and +1.74% / +3.01%.
One rotated sample reached 58.079B cycles; we report both minimum and median
rather than selecting that slow sample as the headline.

Disassembly confirms that `src-mod-lookup-at` loads the ArrayList length before
the loop. With rotation it also loads the data pointer once after the entry
guard. Hoisting removes about 0.4–0.6B retired instructions in the full workload,
but the local improvement does not establish a whole-workload cycle gain.
Neither option enters the best runtime policy; the induction baseline remains
about 1.27× LLVM in these fresh comparisons, above the 1.10× target.

## Generation cost

Three alternating rounds with the same candidate and fixed source, using
`COIL_CODEGEN_TIMINGS=1`. These are IR-to-machine generation times, excluding
frontend work. Raw results, compiler/source identity, commands and compressed
per-function timing logs are under `generation/`.

| Policy | Minimum seconds | Median seconds | Increment vs induction |
|---|---:|---:|---:|
| Induction | 9.716431 | 9.766328 | — |
| Hoisting | 10.435370 | 10.501811 | +7.40% / +7.53% |
| Hoisting + rotation | 13.044064 | 13.081695 | +34.25% / +33.95% |

All three emits of each policy produce identical bytes. Host object hashes:

- Induction: `221639412cd1c1c5dd75b714943a35c3043deeed7c27fbdae1fbc55582b9f09b`
- Hoisting: `196702466ec6eaffc1b9d902a579034663b842393a8a7cf787d0fbe70637bdf8`
- Hoisting + rotation: `74eeb53016e24f91fb898421894d66f97f01b6b08709aecfa91d19ce56669733`

This increment does not remeasure LLVM generation; no absolute 5× claim follows
from it. The runtime-first permission allows this cost for research, but the
combined target remains unmet. Nothing is installed or pushed.

## Completed validation and retained state

All 300 standalone library programs ran: 298 pass. The two failures are the
previously documented `jit-parameter-specialize` ("expected expansion") and
`private-leaf` ("wrong signature accepted"). No additional failure was found.
All 73 linked AOT consumers pass using 5,410 freshly generated fixtures, copied
to a private directory with hashes recorded. The generic standalone runner
omits link flags; its linked-consumer failures are superseded by this proper
linked run. Results and the two known failure logs are under `validation/`.

Quick FAST passes with induction and hoisting enabled (63s under concurrent
validation load; not a performance measurement). Full FAST, live emission and
current-source full bootstrap remain eventual acceptance gates for the overall
goal, which has not been met.

The final candidate was rebuilt after vendoring and the provenance update.
It emits byte-identical hoisted and rotated objects to the measured hosts.
Default output also matches the preceding induction generator exactly:
`3a9ae51cf16cdbdbcb309b77d3463ad54bf0ee244f70b73f6545b087866804c8`.
That is a different check from the fixed workload's `9d775276...` seed: the
research generator already contains retained allocation-region changes, whereas
the measured hosts compile the fixed older backend source. See
`final-identity.json` for measured and rebuilt generator identities.

Integration commit: Coil `6d1cccbb` on `research/loop-load-hoist`.
The source and vendored library trees match byte for byte. The pass remains
available as a validated, opt-in research component, but the best runtime policy
continues to omit both load hoisting and rotation. No install or push occurred.
