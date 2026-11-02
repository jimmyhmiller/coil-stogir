# Architecture contract

The reference is dstogov/ir commit
`92171d0a4a36b0acf707f2dea7998de615dd4acd`, specifically
`ir.h:ir_jit_compile` and `ir_main.c:ir_compile_func`. Attribution and license
terms are centralized in [PROVENANCE.md](PROVENANCE.md), [NOTICE](../NOTICE)
and [LICENSE](../LICENSE).

## Pipeline and current gaps

| Upstream optimized stage | Coil implementation and status |
| --- | --- |
| Construction folding/CSE, def-use lists | Compact graph, builder/fold modules and uses. Implemented coverage does not imply all upstream folds. |
| Optional mem2ssa, then reset CFG | Not implemented. |
| SCCP at optimization levels above one | Lattice and worklist prerequisites exist. Analyzer, rewriting and iterative optimization are not enabled. |
| CFG, dominators, loops, GCM, scheduling | `pipeline.prepare` orchestrates CFG, dominance, loop depth, placement and scheduling. Full upstream algorithm parity remains unverified. |
| Target matching | `a64.compile.generate` builds a persistent `a64.match.Plan` before register analysis. Fusion and reuse coverage remain incomplete. |
| Virtual registers, live ranges, coalescing, allocation | Matched operands feed register liveness, ranges and constraints, then split-interval allocation. Explicit upstream coalescing and full allocation-policy parity remain open. |
| Block scheduling and emission | Post-allocation block ordering and native emission. The scheduling core has a pinned-upstream differential; this does not establish whole-pipeline equivalence. |

The current entry point has one preparation/allocation path. It does not yet
implement upstream's distinct O0/O1/O2+ option and flag policy. Accepting `-O3`
in the Coil CLI must not be described as enabling the missing upstream passes.

## Invariants for further work

- Keep the compact signed-reference graph as the semantic IR. Pass facts,
  schedules and machine constraints may index it; they must not become an
  independently maintained replacement IR.
- Put optimizer algorithms in the standalone library. The Coil adapter
  translates CIR and supplies policy; it must not recognize benchmark code.
- Perform matching before liveness. Fused operands and reuse requirements must
  reach allocation rather than being hidden in a late emission shortcut.
- A graph rewrite must preserve or explicitly remap observable roots, Phi
  predecessor correspondence and live references. Invalidate/rebuild affected
  uses, CFG, dominance, loop, placement, schedule and matching facts before use.
  Storage-level rewrite APIs alone do not satisfy this pass contract.
- Keep a working graph alive until pending graph references have been resolved
  into the owned image. Compilation must preserve the caller's graph when the
  API promises immutable input.
- JIT and AOT consume the same relocatable image. There is no alternate optimizer
  or LLVM/TPDE fallback behind either path.
- Keep all optimization, matching, allocation and image generation inside the
  measured IR-to-machine-code boundary.

## Extensions and sequencing

Automatic loop vectorization is an independent extension, not a ported feature
of the pinned upstream pipeline. Its current analysis work is isolated in
`.worktrees/loop-vectorizer` and is not connected to the delivered compiler.
It must not substitute for completing the missing upstream optimizer stages.

The next upstream implementation priority is the SCCP analyzer and rewrite
pipeline, followed by explicit mode policy and the remaining matching,
coalescing and allocation gaps. Each stage needs semantic execution tests and,
where practical, differential checks against the pinned implementation.

Any future vector transformation must operate on the same graph before final
matching/liveness, rebuild invalidated analysis, prove memory dependence safety
(or guard it at runtime), preserve scalar fallback and tails, and pass both JIT
and linked AOT execution tests. Analysis-only fixtures do not establish a safe
transformation or a performance improvement.
