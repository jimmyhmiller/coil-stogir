# Canonical spill-home architecture audit

Pinned upstream ir_ra.c:4203 marks split parents SPILLED, assigns shared homes;
assign_regs:4435–4558 stores definitions (except proven reuse) and marks operand
reloads using per-interval/per-block availability; needs_spill_reload:4332 walks
predecessors. It does not blindly materialize every contiguous child boundary.

Our current native emitter instead derives contiguous child transfers and emits
them at use/definition boundaries. General odd reloads are intentionally rejected.
Original has four LOAD/USE/DEF/SAVE subpositions; ours has two. Upstream split
inside a range retains a use at the cut, while our end-exclusive split puts uses
at the cut in the suffix. Copying positions without this adaptation is unsafe.
Do not enable free/reload loop cuts before their transfer protocol is valid.

The captured actual provider replay remains byte-identical to current Coil:
1464bytes, SHA97dcf1a1c7350db51fb2fd7a688a85a0f380f2487565dcd42180d9a4fa9c505d.
Generator records every machine definition, coalesced owner, split transfer and
natural-loop depth. Several values defined outside inner loops are stored inside:

| Parent | Definition position / depth | Existing home store / depth |
|---|---|---|
|134|9 /0|171 /1|
|350|71 /0|419 /3|
|255|155 /1|376 /3|
|257|157 /1|419 /3|
|259|159 /1|419 /3|
|630|169 /1|383 /3|
|298|311 /2|383 /3|
|299|317 /2|383 /3|

These are candidate repeated stores, not a measured performance win. Correct
adaptation can establish canonical homes after definitions, then suppress boundary
stores only when every changing/coalesced definition and incoming Phi is covered.
Definition writeback may be placed at the next even phase before the following
instruction: ordinary valued definitions do not terminate blocks, and such moves
must be visible to layout and simultaneous transfer planning. Calls/stack Params,
spilled definitions, Phi edges, aliases, scalar/FP/vector widths, unsafe frame
introspection, external entries and failure cleanup need explicit validation.
Existing homes only are a first stage; broader split/reload policy remains open.
No production algorithm change or runtime claim in this checkpoint.
