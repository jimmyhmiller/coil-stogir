# Literal property mask declarations

Same ten-million-iteration feedback workload and compiler as the property-flag
comparison; four builds, one excluded warmup, five alternating process samples.

| Masks | LLVM O3 seconds | stogir O3 seconds |
|---|---:|---:|
| def globals |0.09096441604197025|0.10231408302206546|
| compile-time const |0.03757541696541011|0.10139737499412149|

Both compilers produce checksum9979482367440117777. Const declarations correctly
represent these literal masks. LLVM benefits substantially; stogir remains
2.70× slower. The earlier near-LLVM scalar-flag comparison applies only to the
def-global representation and must not be generalized as backend parity.
The shape-slice removal remains a measured large stogir improvement. The backend
still needs stronger simplification of boolean control and repeated loads.
ASAN checks cover all131 entries and invalid opcodes. Raw samples are adjacent.
