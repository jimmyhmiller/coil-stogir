# Keep relocatable symbol materializations near their uses

The retained scalar verifier object materializes many symbolic string addresses
before a loop and keeps them live throughout it. They are positive BITCASTs of
negative named address constants. Ordinary numeric literal folding does not
replace them, because the relocation must survive. The default GCM minimum-loop-
depth policy hoists these pure casts even when their only use is a conditional
store inside the loop, increasing register pressure on unrelated hot paths.

The experiment retains the existing checked earliest/latest dominator interval
and use-block computation, including Phi predecessor handling. For a BITCAST
whose sole source is a negative named constant, it selects the latest common-use
bound instead of the minimum-loop-depth block. All other placement is unchanged.
No graph references, roots, memory effects, aliases, ABI or relocation encoding
are rewritten; no node is cloned or new allocation exception introduced. This
is an independent materialization cost policy, not a port of an upstream GCM
rule or a substitute for full constant rematerialization. Hot repeated symbol
uses may favor hoisting, so compiler-wide adoption requires measurement.

The initial owning-Graph copying hypothesis was rejected: Coil ordinary struct
parameters are immutable references. No borrowed-view API was implemented. The
first fixture recompilation used an unchanged compiler backend and therefore
could not exercise the edited standalone placement pass; it is discarded.

The controlled generator instead runs the local library's O3 image pipeline on
an identical16-condition loop. A second source root retains74530b8 placement;
source and object hashes verify the distinction. Both generators check native
string-address observations. One independent C caller checks49 combinations of
zero/small counts and selectors including unsigned wrap, complete destination
canaries and a zero-trip null output. Eight alternating process-CPU samples
after excluded warmups measure4x1M iterations with no symbol stores taken.
Before23.1880ms, latest17.9165ms; the selected frame shrinks160 to32bytes.
This is a compiler-pattern reduction, not bootstrap acceptance. Raw evidence is
in validation/symbol-cast-placement. Compiler integration is not yet adopted.


Broader debug/ASAN placement, native loop, switch-loop, call and composed-module
execution suites pass. Validation transactions retain all1188x25 diagnostic
cases. No full compiler result, installation or adoption is established.
