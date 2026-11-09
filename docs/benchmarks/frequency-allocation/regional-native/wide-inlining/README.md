# Broader inlining with regional allocation — experiment in progress

The broad rotation control has built successfully. The regional host is still building from the same fixed compiler source and preserved generator. Neither broad build is a serial generation measurement: preparation overlapped other build/validation work.

A one-second, 10ms-interval `sample` of the active compiler showed 83 samples in the compilation thread: 44 in the transfer-construction branch (43 directly in `allocation-transfers.build`), 39 in the scoped recoloring branch (36 directly in `run-scoped!`). This short sample is a local bottleneck clue, not a whole-build percentage estimate. Raw sampling output is archived alongside this note. Source inspection shows internal transfer discovery scans all parts at every schedule position, and scoped interference construction checks every pair, including frozen/frozen pairs. Later generation work should preserve exact transfer order, domains, search decisions and emitted bytes while improving those algorithms.

The intended runtime comparison is a two-by-two test: retained-small vs broad inlining, each with rotation alone vs rotation plus regional allocation, with a fresh LLVM control. Wait for all task-owned build/test work to finish, alternate the five hosts serially for three rounds, and require the fixed seed output hash for every run.

The broad inline policy is `budget=4096,template=2048,small=256,small-scope=any,hoist=1,always=1,pair=1,indirect=1`. All four Stogir hosts use loop eviction/reloads, prediction and induction. Generation cost recovery is deferred until the runtime experiment supplies a result. No policy is promoted on the basis of these pending builds.
