# Exact regional setup improvements

The broader-inlining build exposed repeated work in allocation setup. Two algorithmic changes preserve the search policy: internal transfers now visit actual child starts using a schedule-position cost table, and scoped interference construction omits pairs whose two endpoints are both frozen. The original allocation is independently verified before search; frozen singleton domains cannot remove one another's currently valid assignment. All edges touching a mutable piece remain, in the same order.

The transfer list retains exact site/part ordering, weights, recipes and machine-phase constraints. The existing final stable site sort restores the original position-first order. No allocation region, search limit, score, register policy or validation gate changes.

`oracle.py OUTPUT` constructs an isolated copy of the current library and inserts comparison wrappers against the implementation at `579c817`. Every transfer field is compared in order. All domains are compared, and every interference list is checked against the old list filtered only for frozen/frozen edges. The compiler uses the new results. The oracle lives only in this isolated validation copy.

The captured real graph passes these checks for all nine regions, keeps the exact before/after scores and accepted transactions, and emits the same object SHA-256 `66227a67864cfce82dd8f00e9fc4910c468f3da570e85caf02beed778778235b`. The nested-loop JIT fixture also passes the old/new comparisons and its independent native answers. Scoped/frozen, whole-child recoloring, native call-pressure and C-linked nested-loop tests also pass. Full compiler object identity checks are in progress. No generation improvement is claimed before measurement.


The first setup version also reproduces the complete retained-small compiler object exactly (`edef6c97eca066a38ce0248faba34dd34b51441c7b463ddafcdd8ef11dd13a46`), and its rebuilt candidate passes quick FAST (48.1s under concurrent build load, not a performance measurement). Its host build reports 171.099s generation under concurrent load; do not compare this as a controlled speedup against the earlier serial measurement.

The traversal now also indexes the next mutable piece, avoiding enumeration of frozen/frozen pairs altogether. Its retained i/j order is identical to the previous upper-triangle scan. The exact transfer/domain/interference oracle passes again for the captured graph, scoped and whole-child tests; the captured object remains byte-identical. Nested-loop JIT passes. Updated full compiler identity builds follow.


Latest source is library `5955426`, Coil integration `115f3f72`; candidate and source hashes are in `metadata.json`. Latest quick FAST passes (46.8s under concurrent builds). The first setup version's incomplete broad host build was stopped with SIGTERM after its retained-small identity check; it is not a completed generation or runtime result. The original broad regional build continues unchanged under the original preserved generator. A one-second sample from the incomplete updated broad build had 77 of 83 compilation-thread samples in `allocation-recolor.score`: an example of the remaining search cost, not a whole-build profile. No further policy or scoring changes were made.

The full library and 73 linked-consumer run in the parent report applies to `579c817`. These exact setup changes have the focused oracle/native checks and compiler integration checks described here; that full suite has not been repeated after them.


The latest retained-small full compiler build is now complete and reproduces `edef6c97eca066a38ce0248faba34dd34b51441c7b463ddafcdd8ef11dd13a46` exactly, matching both the original regional host and the first setup version. Build output reports 161.307s generation while the original broad build was running; this is not a serial generation measurement. No runtime rerun is needed to establish that these object bytes are unchanged. The joint performance target remains unmet.
