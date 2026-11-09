# Exact incremental allocation scoring

Broader-inlining research is waiting on a very expensive allocation search. This change reduces repeated scoring work without changing the cost function, search order, bounds, regions or accepted-transaction checks.

A sparse child-to-transfer-site incidence index includes every logical copy, including currently free identity copies. The baseline stores each site's complete cost. A proposal changes at most a few children: collect their incident sites, recompute each affected site in full (including duplicate physical pairs involving unchanged copies), and add the difference to the baseline. Marked-site scratch storage is cleared after every query. A committed assignment refreshes all baseline site costs before the next round. Child and copy identities remain immutable within a search invocation.

The old full `score` function is unchanged and still checks every committed transaction independently. Existing standalone `search!` and `offer!` signatures remain available; the full run shares the index across all proposals.

`tests/allocation-cost.coil` compares 6,480 distinct proposal/baseline combinations against the full scorer, repeats each query, refreshes baselines, and covers omitted changes, shared parent spill identities, physical duplicates, constant/frame recipes, dormant identity copies, a child with no transfers and an empty copy graph. Whole-child recoloring and the nested-loop JIT/C-linked tests pass.

The isolated oracle builder `../indexed-setup/oracle.py` additionally checks every proposal's incremental score against the full scorer during actual search, while retaining the previous transfer-list and domain/interference checks against `579c817`. Both the captured compiler function and nested-loop fixture pass. The captured object remains SHA-256 `66227a67864cfce82dd8f00e9fc4910c468f3da570e85caf02beed778778235b`, with identical nine-region costs and accepted transactions. Updated compiler integration, full-workload identity and timing remain next. No generation speedup is claimed yet.

The existing Coil field-vector `for` expansion issue recurred during development. A reduced current-compiler reproduction and an explicitly typed slice control were checked, and evidence was added to the existing `coil-bugs` cell `for-field-vector-iter-missing-argument`; no duplicate bug or compiler fix is claimed.

Compiler integration `2b02902e` vendors library `59edaf4` unchanged. Generator SHA-256 `4d06a5b2a1eb9681aa4be70ce5996199200454e6ab6e4a30d86b026203044b7c` is preserved under integration `build/regional-native/incremental/`. Retained-small regional, broad regional, broad rotation control and regional-plus-load-hoisting hosts are building. These overlapping builds are preparation, not benchmark timings. The whole-child native oracle also passes.

The updated generator reproduces the complete retained-small regional compiler object (`edef6c97…`) exactly. Quick FAST passes; its 75.7s duration exceeds the advisory 60s target under concurrent build load and is not performance evidence. The hoisting/rotation native test also passes with regional allocation enabled. Runtime comparisons and serial generation measurements are still pending.

The broad rotation-only host also reproduces its original object exactly (`ed8b4625…`). The broad regional host is still building. The planned runtime comparison adds regional-plus-hoisting to the original five hosts, so its effect is measured against the same-period regional control.
