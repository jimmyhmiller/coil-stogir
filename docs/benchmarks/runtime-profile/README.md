# Current-host dynamic profile refresh

The latest loop transformations change local machine code but have not closed the whole-workload gap. Refresh the dynamic profile before choosing another transformation. The initial comparison is between fresh regional, strength, and hoisting-plus-strength hosts, so additional loop-carried values can be traced to their dynamic costs.

`prepare.py SOURCE OUTPUT` copies the compiler sources into a new diagnostic directory and adds block counters there. Production sources and the existing audit worktree remain untouched. The only compiler changes are a diagnostic module, one emission hook at physical block labels, and adapter hooks to enable counting and identify functions. Without `COIL_STOGIR_BBCOUNT=1`, the emitter adds no instructions; validate byte identity against the ordinary control host.

Each counter uses reserved x16/x17 and six instructions that preserve NZCV. A separate dylib maps a 64 MiB array at the requested address using a non-destructive mmap hint, refusing a different address. The source refuses counter indices beyond that extent. Counting requires serial execution. Both the generator and counted host load the runtime, because native compiler helpers can execute while the generator emits code. Counter hosts are diagnostics, never cycle-timing evidence.

Validate each counted host by emitting the unchanged fixed compiler workload and requiring seed SHA-256 `9d775276a9d02daf921868c2bbca12344b97c4fa596a78bf0a75393ae24028cb`. Preserve generator/host identities, the map, counts, and disassembly. Decode with the existing `mixdump.py` tooling from the integration checkout; copy the exact tool used into the evidence directory.

Physical block execution counts are exact for the serial run, subject to 64-bit counter overflow not occurring. Derived instruction mixes are estimates: emitter-created branches/stubs and prologues lack independent counters, and code after unconditional terminators is excluded. Do not equate their sum with the hardware instruction count. Profile counts guide investigation only; no measured weights or workload identifiers enter production policy.

Status: instrumentation prepared, not yet built or validated. The six-host ordinary runtime comparison is still running; all diagnostic builds wait until it finishes.
