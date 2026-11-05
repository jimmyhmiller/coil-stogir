# Checked operand access runtime gap

Source b01d83d; preserved Coil a58918c7 candidate. The fixture exports ordinary graph.operand behavior through an opaque C-ABI function. One identical LLVM-built caller checks references -3 through 35 and indexes -1 through 4 against independent expected results, verifies an invalid arity marker, then accumulates 20 million valid accesses with an independent checksum. No backend checks are disabled.

Eight rotating generation samples and twelve CPU samples after excluded warmups:

| Backend O3 | IR-to-machine-code ms | Caller CPU ms | Object bytes |
|---|---:|---:|---:|
| Stogir | 1.5545 | 80.7520 | 2290 |
| LLVM | 21.5920 | 30.8630 | 1616 |

Stogir generation is 13.89× faster here; runtime is 2.6165× slower. This is an isolated diagnostic, not bootstrap acceptance. Fixed caller overhead is included in both runtime figures. All per-backend objects are stable. Raw samples, hashes, assembly and reproduction script are in operand-control-gap/.

## Concrete differences

In the full-verifier object, graph.operand has 97 Stogir instructions versus 24 LLVM instructions. In this isolated object it is inlined into the exported wrapper: Stogir emits 115 instructions versus LLVM 32. These static counts are not execution counts or attributed runtime percentages.

Stogir retains a second positive-reference test and a negative-reference path after the caller has already rejected nonpositive references. Existing dominating-truth recognizes exact predicates along straight control chains and stops at merges. It does not provide general path-sensitive value ranges.

Stogir also retains a 16-byte Option result frame, storing its tag with STR X and reading the tag through a W value. The exported wrapper contains stack stores/loads and an explicit tag switch that LLVM eliminates. mem2ssa.cell! requires exact equal offset and width for overlapping accesses. Thus a 64-bit tag store and 32-bit tag load cannot share a promotion cell. Existing load forwarding can extract contained views locally, but does not by itself construct SSA across this joined memory state.

The next optimization investigation should cover private mixed-width fields across branches, preserving initialization, all observed bytes, escape checks, endian policy and pointer/BOOL constraints. Do not accept differently sized overlap unconditionally: partial stores can leave observable bytes unchanged. Redundant predicate elimination is a separate general control optimization. Neither contribution has yet been quantified independently or proved dominant in the full bootstrap.

No compiler installation changes. This diagnostic contains no backend semantic change.
