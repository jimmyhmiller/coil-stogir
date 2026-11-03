# Fixed-use event index component

The existing pressure policy now uses sorted per-register fixed-use events and exact split ownership. The old full-scan and fixed-part-index queries remain as oracles/compatibility entries. All three pressure vectors are preserved, including fixed uses outside their owners' live ranges. Every grant, spill-prefix and eviction split updates a persistent ownership forest. Queries lazily compress ownership paths.

The assigned-range scan remains. This is not a complete active/inactive allocator port and does not establish the full compiler goal.

A small synthetic call-reservation workload compares previous pressure discovery with the event query. Both paths consume all8 registers of all3 pressure arrays in a checked checksum. Each query has one range spanning a call. Initial parts/reservations, index construction, queries and cleanup are included in whole-process timings. The executable is LLVM O3, compiled by installed Coil156a7e3b. Three measured alternating samples follow one excluded warm run per mode.

| Queries |Old scan median s|Event-index median s|
|---:|---:|---:|
|256|0.012782833|0.007442292|
|1024|0.057637083|0.021647083|
|4096|0.876582875|0.289432416|

The largest case improves3.03×, but remains quadratic because assigned physical intervals are still scanned. The256-query process is dominated by startup/noise. Raw samples, source/binary hashes and benchmark source are retained; these numbers are pressure-kernel evidence, not full compiler compile times. An earlier preliminary checksum consumed only fixed-at; the table uses all three vectors.

A stogir-built executable passes the256-query checksum in both modes (one correctness run each; not runtime medians). ASAN passes the expanded pressure oracle, split allocation, wide/narrow call pressure, scalar/floating/checked/switch pressure, dynamic stack scopes and stencil vectorization. The seeded oracle includes1/4/16/64 register domains, holes, repeated splits, negative-parent reservations and out-of-range fixed uses. A targeted sequence invokes every tracked mutation, including eviction's nested spill split.

Next, remove the remaining whole-part assigned scan using immutable canonical physical-reservation range indexing plus an expiring active/inactive assigned-value collection. Canonical reservations have one fixed use at their single range's start; other supported inputs need the general path. Preserve exact next-use behavior for long incoming reservations, self exclusion and lifetime holes. Validate against the full-scan oracle before compiler integration. No new compiler installation or full bootstrap measurement is claimed for this isolated component.
