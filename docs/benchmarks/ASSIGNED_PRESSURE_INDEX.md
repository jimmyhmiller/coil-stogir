# Assigned-pressure query component

The solver composes exact fixed-use events with an immutable reservation range
index and an expiring assigned-value collection. Allocation policy and all
checks remain enabled. The old full scan remains the differential oracle.

The synthetic pressure workload consumes all8 registers of all3 pressure vectors
in a checked checksum. Whole-process times include index construction and cleanup.
LLVM O3 executable, three measured rotating samples after an excluded warm run:

|Queries|Old scan s|Fixed events only s|Combined index s|
|---:|---:|---:|---:|
|256|0.011567417|0.006962500|0.005794000|
|1024|0.061044458|0.021394208|0.005510916|
|4096|0.931483417|0.287344541|0.013108542|

The largest reservation-heavy kernel improves71.1× over the old scan. This is
not a whole-compiler speedup. Startup/noise dominates the smallest cases. A
stogir-built executable passes small scan/event/state and large state checks;
those one-run smoke times are not runtime medians. Raw samples and source hashes
are retained beside this report.

ASAN passes the old, event/split and monotonic assigned-state oracle configurations,
including long incoming reservations, holes, negative-parent and noncanonical
parts, out-of-range fixed uses, self exclusion, repeated positions and actual
split/eviction/expiration mutations. Split allocation and native scalar/call/FP/
checked/switch pressure, dynamic stack scopes, over-aligned frames and stencil
checks pass. Full compiler integration and acceptance remain pending.
