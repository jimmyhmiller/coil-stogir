# Regional zero-trip allocation evidence

This checkpoint establishes an emission result, not a workload speedup. The
actual zero-trip path of `primitive-providers-in` can avoid the three outer-value
reloads. The assignment is legal and can be found by a bounded, solver-free
search using static branch predictions. The compiler does not yet select and
apply these regions natively. Runtime and generation targets remain unmet
together; the previous whole-function recolorer remains disabled.

## From feasibility to a generic search

The unrotated region (blocks 321, 55, 16) admits a six-group assignment with no
memory copies on 16→54, but its loop-depth transfer cost increases from 503,298
to 522,498. It moves transfers onto recurring inner-loop paths. The archived
`sat.json.gz`/`sat.log.gz` record allocation-verifier evidence only.

Rotation separates the entry guard from the inner loop's backedge. In region
321, 664, 678, 636, six changed groups retain outer parents 209, 620 and 132 in
registers 26, 22 and 25. Guard temporaries 283, 286 and 287 move to caller-saved
registers. Transfers then occur at body entry/exit. An exact finite-domain
optimization proves the lowest loop-depth cost satisfying no exit copies is
478,300, versus 477,940 before these splits. This result starts after global
recoloring. `constrained_optimize.py` is a diagnostic for this fixed captured
region, never a compiler rule.

The full native fixture validates all original child assignments, ranges and
homes before changing them. It uses public allocation and emission APIs, the
independent allocation checker, and an unchanged preserved-register set. Its
control object is byte-identical to the actual rotated/global-recolor object:
`a4e052a1f080dfc04bc0b19198632081aa3cfa6b5fd7de86b3c9f61cfe65d04d`.
In the hypothesis, the zero-trip branch at 0x158 targets 0x448, after the three
reloads at 0x438, 0x43c and 0x440. Static code grows from 358 to 363 instructions;
the traffic has moved, not disappeared globally. Some eager canonical-home
stores still precede the guard.

## Why balanced flow matters

The existing layout estimator omits backedge contributions and multiplies loop
headers by ten. It is useful for layout ranking but does not conserve execution
counts. That estimator still rates the regional change slightly worse.

Using the *same branch probabilities* in `(I - P^T) f = entry` changes the ranking:
30,003,634 → 29,941,531 integer proxy units (scale 10,000). The guard is predicted
to enter the body 75% of the time. No measured profile or rare-body override is
used. The independent dense partial-pivot solve has residual 1.91e-14.

`stogir.flow-frequency` implements sparse elimination with positive M-matrix
pivots, normalized positive edge weights, unreachable-component handling and a
residual check. Closed recurrent or numerically unreliable systems decline with
`None`; invalid inputs return an error. `block-layout/expected-frequencies`
shares the existing prediction weights without changing the layout algorithm.
All 132 native frequencies match the independent solve within 1.01e-6, including
printing truncation. The new API is not yet called by allocation.

## Bounded search without global recoloring

`regional_search.py` discovers regions from CFG edges and loop depth. It starts
at a two-arm branch where one single-successor chain enters a deeper loop, then
collects the other same-depth forward corridor. Regions run smallest first.
Original children can split at existing block boundaries, retaining lifetime
holes and use constraints. Later regions keep already-different assignments
separate. The ejection search tries available registers before occupied ones;
limits remain depth 3, 100 visits per root, 8 changes per transaction, 32 rounds.
Only strictly improving, phase-legal transactions are retained.

Starting from the ordinary rotated allocation (no global recoloring), the
complete transfer proxy drops 54,072,862 → 34,290,177. All three memory copies on
636→628 disappear; two register moves remain. The scalar replay model's phase
check is not a replacement for the native machine-definition bridge, particularly
for multi-output selections.

The resulting full native fixture succeeds with 3,211 baseline assertions and
94 per-block assignments across the discovered regions. Its empty-loop branch
at 0x178 targets 0xc8, performs two register moves, and jumps to 0x480. The three
body-exit reloads at 0x468, 0x46c and 0x470 are skipped. Object hashes are in
`metadata.json`. This captured function has **not been executed**; emission,
allocation verification and code inspection establish feasibility, not semantic
or performance acceptance of a native regional pass.

## Reproduce from the library worktree

Decompress `rotated.trace.gz`, `rotated-replay.log.gz`,
`native-flow-probe.coil.gz`, and `native-flow-probe.log.gz` into `build/zero-trip/`.
The generated probe uses that directory for output. Use the fixed compiler from
`metadata.json` with `COIL_LIBRARY_STATE=0`, `run`, `--backend stogir -O3
--no-debug --debug-checks`.

```
python3 docs/benchmarks/frequency-allocation/zero-trip/regional_search.py \
  build/zero-trip/rotated.trace build/zero-trip/rotated-replay.log \
  build/zero-trip/native-flow-probe.log build/zero-trip/reproduced-search.json
```

This writes both the assignment and an independent library allocation-checker
program. Run it with the fixed compiler. To regenerate the full native fixture,
decompress `../native/graph-replay.coil.gz` to `build/zero-trip/graph-replay.coil`:

```
python3 docs/benchmarks/frequency-allocation/zero-trip/native_fixture.py \
  build/zero-trip/rotated.trace build/zero-trip/rotated-replay.log \
  build/zero-trip/rotated-replay.log build/zero-trip/reproduced-search.json \
  build/zero-trip/graph-replay.coil build/zero-trip/native-search.coil \
  --prefix build/zero-trip/search
```

`native-search.coil.gz` is also archived directly. The constrained optimizer
additionally requires `../native/graph-rotated.log.gz` at
`build/native-recolor-v2/graph-rotated.log` and Z3. Its hardcoded block references
specify the diagnostic question, not an optimization policy.

Validation: new flow-frequency analytic tests pass in JIT and a separately
built AOT executable; existing branch-predict and block-layout checks pass.
The full captured native flow/assignment probes emit successfully. No full
suite, Coil integration rebuild, whole-workload timing, installation or push is
claimed for this checkpoint.

The ordinary compiler entrypoint also reproduces the regional control object
exactly (`dc4ce7e7…`); the diagnostic driver has not changed the baseline pipeline.

Next: native region splitting and scoped recoloring, exact machine-phase copies,
then targeted JIT/AOT semantic tests and full same-source workload measurements.
Keep cost construction, selection, splitting and ABI/frame finalization generic.
