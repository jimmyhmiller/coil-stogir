# Opcode property kernel

Same O3 compiler, unchanged source workload across old/new libraries and both
backends, local macOS AArch64. Ten million dependent iterations; every class
observation feeds the next opcode index. One excluded warmup, five alternating
measured process executions. Library cache disabled, serial compilation.

| Library | LLVM O3 seconds | stogir O3 seconds |
|---|---:|---:|
| Shape slices | 0.0912628750083968 | 0.4579179169377312 |
| Scalar flags | 0.09268029197119176 | 0.10337299993261695 |

Stogir runtime falls 77.4%; updated stogir remains 11.5% slower than updated
LLVM on this kernel. This does not establish full compiler acceptance or a
compile-time improvement. All checksums match 9979482367440117777. Raw samples
and workload hash are in opcode-properties/runtime.json.
