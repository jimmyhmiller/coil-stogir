# Checked AVec access from the generated compiler profile

The installed source 675c94ae remains outside the full compiler performance target. Its matched diagnostic measures a 3.90x IR-to-machine-code advantage over LLVM O3 and a 3.27x slower native self-rebuild. See REGISTER_RESULT_COMPILER_CHECKPOINT.md.

A clean three-second early frontend sample shows checked AVec access and trie lookup among the worker thread's most frequent native leaves. Main-thread wait samples are excluded. This sampling window is evidence for choosing a workload, not a full-run percentage attribution or acceptance timing.

`benchmarks/compiler-gaps/avec-get.coil` performs checked access to a 16-byte compact node. The opaque runner creates 4,096 elements, crosses trie levels, and performs 20 million calls. Every backend uses the same LLVM-built runner object and returns checksum 859763163008. Source and runner object hashes, all samples and compile diagnostics are retained in `avec-frontend-profile/avec-get-comparison-results.json`.

| Backend | Median runtime | IR-to-code diagnostic | Object bytes |
|---|---:|---:|---:|
| stogir O3 | 0.14625125005841255 s | 0.008311 s | 13,512 |
| LLVM O3 | 0.04818241705652326 s | 0.041430 s | 7,352 |
| TPDE | 0.21731141593772918 s | 0.000269 s | 10,534 |

One warmup is excluded; five measured samples alternate backend order. Small compile diagnostics are single samples and do not establish the full compiler target.

Template tracing finds a 16-cell accessor containing calls, a 60-cell trie helper containing a loop, and a 152-cell bounds checker. The delivered graph inliner rejects loops and nested calls. Removing checks or forcing source Always policies would change the experiment and is not an acceptable fix. The next bounded component supports closed returning loops through the existing two-phase graph clone; nested direct calls and preservation of cold terminal paths require separate validation.

The clean sample summary is `avec-frontend-profile/register-frontend-profile-clean-summary.json`. Raw macOS process/binary inventories are not part of the report.
