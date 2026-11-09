# Exact regional setup improvements

The broader-inlining build exposed repeated work in allocation setup. Two algorithmic changes preserve the search policy: internal transfers now visit actual child starts using a schedule-position cost table, and scoped interference construction omits pairs whose two endpoints are both frozen. The original allocation is independently verified before search; frozen singleton domains cannot remove one another's currently valid assignment. All edges touching a mutable piece remain, in the same order.

The transfer list retains exact site/part ordering, weights, recipes and machine-phase constraints. The existing final stable site sort restores the original position-first order. No allocation region, search limit, score, register policy or validation gate changes.

`oracle.py OUTPUT` constructs an isolated copy of the current library and inserts comparison wrappers against the implementation at `579c817`. Every transfer field is compared in order. All domains are compared, and every interference list is checked against the old list filtered only for frozen/frozen edges. The compiler uses the new results. The oracle lives only in this isolated validation copy.

The captured real graph passes these checks for all nine regions, keeps the exact before/after scores and accepted transactions, and emits the same object SHA-256 `66227a67864cfce82dd8f00e9fc4910c468f3da570e85caf02beed778778235b`. The nested-loop JIT fixture also passes the old/new comparisons and its independent native answers. Additional focused oracle tests and full compiler object identity checks are in progress. No generation improvement is claimed before measurement.
