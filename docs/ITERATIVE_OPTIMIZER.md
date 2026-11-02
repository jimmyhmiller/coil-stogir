# Incremental optimizer development

Reference: dstogov/ir `92171d0a4a36b0acf707f2dea7998de615dd4acd`,
`ir_sccp.c:ir_iter_fold`, `ir_iter_replace_insn`, `ir_iter_find_cse` and
`ir.c:ir_folding`. Attribution remains centralized in NOTICE and PROVENANCE.

`iter-fold` is an incremental scalar fold/CSE/DCE kernel. It consumes explicit
seeds, maintains the existing use lists, and revisits affected users and former
inputs. Shared fold decisions distinguish CSE from forced emission, including
hard-copy and invalid-division barriers. Positive observable data references
survive through COPY nodes. The public entry transforms an owned graph and
discards failed output; affected structural analyses must be rebuilt afterward.

This is not the complete upstream `ir_iter_opt`: algebraic rule coverage,
canonicalization, promotion, related-use scheduling and control/load cleanup
remain pending. SCCP candidate transport and mode policy are also pending.
The feature is isolated and no new optimizer is enabled in Coil.

Focused decision-oracle, use-list, JIT/AOT and AddressSanitizer evidence is in
[validation/iterative-fold.json](validation/iterative-fold.json). The decision
oracle checks 16 selected outcomes, not complete fold-rule or transformed-graph
parity. Full standalone and compiler validation remain pending. No new
performance measurement or improvement is claimed.

Selected scalar algebraic rules now cover integer same-reference comparisons,
subtraction and bitwise identities; zero/one arithmetic identities; nested unary
cancellation/idempotence; and scalar identity BITCAST. Literal folds run before
applicable generic identities. Floating counterexamples and mixed-type cases
requiring a restart remain expressions. The expanded native fixture exercises
chained rewrites and verifies 25 JIT and 25 linked AOT answers under the same
worklist and root-preservation contract.

[validation/algebraic-fold.json](validation/algebraic-fold.json) records 272
selected normalized upstream results, including exact constant type/payload or
positive copy target and floating cases that must remain unfurled. Normalization
accounts explicitly for upstream's reserved TRUE/FALSE constant references.
This extends the kernel's rule coverage; it does not complete upstream folding,
connect SCCP candidate transport, or enable optimization in Coil.
