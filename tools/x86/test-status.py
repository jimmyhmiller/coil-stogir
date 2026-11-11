#!/usr/bin/env python3
"""Write tests/X64_STATUS.md: every test file, its category for the x86-64 port,
and for facade tests the operation family that has to work for it to pass.

    tools/x86/test-status.py

Categories are derived from the files; FAMILY below is maintained by hand and
the script fails when a facade test has no family. `family-tests.sh` reads the
table this writes.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS = os.path.join(ROOT, "tests")

FAMILIES = ["integer", "memory+stack", "calls+ABI", "floating", "vector", "switch+control",
            "atomics", "private-leaf/module", "inlining/optimizer", "other"]

FAMILY = {
    "integer": """bit-literal-identities checked-object checked-projection-fold compile-image
        extension-idioms extrema-object
        integer-arithmetic-object jit-bit-test jit-checked-pressure jit-condition-merge
        jit-condition-merge-zero jit-conditional jit-conversions jit-division jit-extend
        jit-literal-operands jit-multiply-literal jit-pressure jit-reciprocal-division
        jit-select-diamond
        jit-subsumed-guard jit-unary-matrix jit-widened-view-bitcast jit-zero-branch macho
        narrow-binary-object narrow-truth-test trunc-view-coalesce unary-object zext-known-zero""",
    "memory+stack": """bulk frame-direct-access jit-bulk jit-bulk-pairs jit-byte-memory jit-local-frames
        jit-local-loop jit-locals jit-memory jit-stack jit-stack-branch jit-stack-invalid
        jit-stack-loop jit-stack-scopes locals sext-load shrink-wrap stack volatile-access""",
    "calls+ABI": """aggregate-result-recursion call-abi-validation grouped-prototypes inline-argval jit-argument-value x64-inline-argval
        jit-call-narrow jit-call-narrow-return jit-call-narrow-varargs jit-call-stack
        jit-call-varargs jit-call-void jit-grouped-arguments jit-hva-abi jit-hva-incoming
        jit-hva-outgoing jit-incoming jit-incoming-fp-layout jit-incoming-widths
        jit-parameter-capture jit-phi-call-redefinition jit-return-piece-placement
        jit-void-return named-call-arguments named-image named-recursion tail-split""",
    "floating": """floating-object jit-floating-arithmetic jit-floating-calls jit-floating-extension
        jit-floating-incoming jit-floating-loop jit-floating-memory jit-floating-phi
        jit-floating-pressure jit-floating-varargs jit-numeric-conversions jit-scalar-truth
        jit-select-floating""",
    "vector": """jit-bulk-pressure jit-loop-guard jit-loop-vectorize jit-loop-vectorize-stencil
        jit-vector-arithmetic jit-vector-bitcasts jit-vector-constants jit-vector-lane-returns
        jit-vector-locals jit-vector-select-returns jit-vector-transport jit-vector-unary
        vector-locals""",
    "switch+control": """forwarded-return-tail jit-equality-chain jit-loop jit-return-tail
        jit-select-dispatch jit-switch jit-switch-direct jit-switch-loop jit-switch-pressure
        jit-termination loop-carried-update-order rotated-test-block switch-prune-default
        terminal""",
    "atomics": "jit-atomics",
    "private-leaf/module": "compile-module-concurrent compile-reads-graph module-execution x64-verify-borrowed-graph",
    "inlining/optimizer": """adjacent-field-promotion backend-validation-proof branch-facts
        call-effect-records copy-forward dead-stores entry-load finite-countdown
        general-if-conversion global-load-forward induction-ranges inline-call-exemptions
        inline-hoist-frames inline-small-callers inline-stack-results jit-boolean-folds
        jit-dead-load jit-iter-fold jit-jump-thread jit-loop-rotate-nested jit-mem2ssa
        jit-optimization-owned-image jit-optimized-entry jit-parameter-specialize
        jit-repeated-expressions jit-return-merge jit-sccp-control jit-sccp-pipeline
        jit-sccp-rewrite load-sink loop-load-hoist loop-rotate loop-strength-native
        memory-countdown partial-field-promotion recolor-native regional-native
        sccp-guarded-dead-arm sccp-rewrite-errors""",
    "other": """compact compile-validation conditional-image conversion-image named-addresses
        phi-captured-metahost validation-transaction""",
}

# Facade tests that need more than the backend to run on x86-64 Linux.
NOTES = {
    "jit-hva-abi": "AArch64 HVA convention. On System V an aggregate of two 16-byte vectors is MEMORY class (by value on the stack, returned through a hidden pointer), which tests/x64-call-abi.coil covers against C; this test itself needs vector values (vector family) and a Coil host callback the Linux compiler cannot build (SysV SSEUP unimplemented)",
    "jit-hva-incoming": "AArch64 HVA convention; Linux Coil compiler aborts (SysV SSEUP unimplemented); System V equivalents in tests/x64-call-abi.coil",
    "jit-hva-outgoing": "AArch64 HVA convention; Linux Coil compiler aborts (SysV SSEUP unimplemented); System V equivalents in tests/x64-call-abi.coil",
    "jit-vector-lane-returns": "x86-64 passes the vector arguments through a machine-code probe (the Linux Coil compiler cannot: SysV SSEUP unimplemented)",
    "jit-vector-select-returns": "x86-64 passes the vector arguments through a machine-code probe (the Linux Coil compiler cannot: SysV SSEUP unimplemented)",
    "jit-vector-arithmetic": "x86-64 leaves out the divisions that trap there (zero divisor, MIN / -1)",
    "jit-vector-constants": "x86-64 pool census excludes all-zero and all-ones constants (built in the register)",
    "module-execution": "prefix image filler is `ret`+`nop` bytes per machine",
}

A64_REASONS = {
    "global-alignment": "hand-encoded AArch64 words and ADRP decoding",
    "jit-hva-varargs": "hand-encoded AArch64 probe function",
    "private-leaf": "hand-encoded AArch64 leaves, register masks",
    "image-alignment": "hand-encoded AArch64 words, Mach-O",
    "image-order": "Mach-O symbol order",
    "jit-external": "hand-encoded AArch64 words",
    "jit-image": "hand-encoded AArch64 words",
    "macho-validation": "Mach-O writer",
    "macho-link": "",
}

# Externs of link partners that are C library functions, not generated objects.
LIBC = {"fork", "waitpid", "signal", "_exit", "alarm", "mmap", "mprotect", "munmap", "getpagesize",
        "memcmp", "memset", "memcpy", "labs", "abs", "malloc", "free"}

HOST_LAYER = {"elf-basic", "elf-validation", "image-layout"}


def read(name):
    with open(os.path.join(TESTS, name + ".coil")) as handle:
        return handle.read()


def main():
    names = sorted(f[:-5] for f in os.listdir(TESTS) if f.endswith(".coil"))
    texts = {name: read(name) for name in names}
    family_of = {}
    for family, members in FAMILY.items():
        for name in members.split():
            if name in family_of:
                sys.exit(f"{name} is in two families")
            if name not in texts:
                sys.exit(f"{name} has a family but no file")
            family_of[name] = family
    rows = []
    guarded = []
    for name in names:
        text = texts[name]
        a64 = sorted(set(re.findall(r'"stogir\.a64\.([a-z0-9-]+)"', text)))
        # The x86-64 backend's own tests: they import its modules directly.
        # `encode` and `registers` alone are the host layer below it.
        x64_backend = (sorted(set(re.findall(r'"stogir\.x64\.([a-z0-9-]+)"', text))
                              - {"encode", "registers"})
                       if name.startswith("x64-") else [])
        family = ""
        note = ""
        if name.endswith("-link") and not name.startswith("x64-"):
            category = "link-partner"
            wanted = set(re.findall(r':as\s+"([A-Za-z0-9_]+)"', text))
            wanted |= set(re.findall(r'\(extern ([A-Za-z0-9_]+)[\s)]', text))
            wanted |= set(re.findall(r'"(stogir_[A-Za-z0-9_]+)"', text))
            wanted -= LIBC
            writers = [other for other in names
                       if other != name and not other.endswith("-link") and "/tmp/" in texts[other]]
            makers = sorted(other for other in writers
                            if any(f'"_{symbol}"' in texts[other] for symbol in wanted))
            if not makers:
                # A generator may build numbered names from a common stem.
                stems = {'"_' + re.sub(r"[0-9_]+$", "", symbol) for symbol in wanted}
                makers = sorted(other for other in writers
                                if any(len(stem) > 14 and stem in texts[other] for stem in stems))
            if not makers and name[:-5] in texts:
                makers = [name[:-5]]
            parts = []
            for maker in makers:
                state = ("ported" if '"stogir.native.compile"' in texts[maker]
                         else "host-layer" if maker in HOST_LAYER else "not ported")
                parts.append(f"{maker} ({state})")
            note = "objects from " + ", ".join(parts) if parts else "objects: see README"
        elif '"stogir.native.compile"' in text or '"stogir.native.private-leaf"' in text:
            category = "ported-to-facade"
            if name not in family_of:
                sys.exit(f"{name} is ported but has no family")
            family = family_of[name]
            note = NOTES.get(name, "")
            if "target/arch-pick (" in text:
                guarded.append(name)
                note = (note + "; " if note else "") + "AArch64 instruction-shape checks guarded"
        elif x64_backend:
            # Before the AArch64 test: an x86-64 backend test may borrow a type
            # from stogir.a64.private-leaf (the shared private-leaf contexts).
            category = "x64-internal"
            note = "imports " + " ".join(x64_backend)
        elif a64:
            category = "a64-internal"
            internal = [m for m in a64 if m not in ("compile", "private-leaf")]
            if internal:
                note = "imports " + " ".join(internal)
            elif re.search(r"machine-code\s+\(Aarch64\)", text):
                note = "probe function written as AArch64 machine code"
            else:
                note = A64_REASONS[name]
        elif name in A64_REASONS:
            category = "a64-internal"
            note = A64_REASONS[name]
        elif name.startswith("x64-") or name in HOST_LAYER:
            category = "host-layer"
            note = "image, JIT or object layer; no backend"
        else:
            category = "neutral-IR"
        if family == "" and name in family_of:
            sys.exit(f"{name} has a family but is {category}")
        rows.append((name, category, family, note))

    counts = {}
    for _, category, _, _ in rows:
        counts[category] = counts.get(category, 0) + 1
    out = ["# Test status for the x86-64 port", "",
           "Generated by `tools/x86/test-status.py`; edit the tables there, not here.",
           "`tools/x86/family-tests.sh FAMILY` prints the test paths of one family.", "",
           "## Categories", "",
           "| Category | Tests | Meaning |", "|---|---|---|"]
    meaning = {
        "neutral-IR": "Graph, analysis and optimizer tests with no backend, JIT or object import. Target-independent.",
        "ported-to-facade": "Import `stogir.native.compile` / `stogir.native.private-leaf` / `stogir.jit.native`. Must pass on both hosts; the gate for the x86-64 backend.",
        "a64-internal": "AArch64 backend internals, hand-encoded AArch64 code, or Mach-O. Not expected to run on x86-64.",
        "link-partner": "Links objects that a generator test wrote to /tmp; runs with `--link-flag` (README). Works on Linux once its generators pass there.",
        "host-layer": "Image, JIT and object-writer layers below the backend, including the `x64-*` encoder, image and link tests.",
        "x64-internal": "x86-64 backend internals (`tests/x64-FAMILY-*.coil`), tested directly against `stogir.x64.*`. Run on the x86-64 host; they skip or check selection only elsewhere.",
    }
    for category in ["neutral-IR", "ported-to-facade", "a64-internal", "x64-internal", "link-partner",
                     "host-layer"]:
        out.append(f"| {category} | {counts.get(category, 0)} | {meaning[category]} |")
    out += ["", "## Families of the ported tests", "",
            "The family is the operation family whose x86-64 implementation the test mainly",
            "waits for. Most tests also need the phase-1 core (integer values, parameters,",
            "compares, branches, PHIs) and many need calls for their harness.", "",
            "| Family | Tests |", "|---|---|"]
    for family in FAMILIES:
        out.append(f"| {family} | {sum(1 for row in rows if row[2] == family)} |")
    out += ["", f"{len(guarded)} ported tests keep AArch64 instruction-shape checks behind",
            "`(target/arch-pick CHECK (do))`: they check behavior on x86-64 and behavior plus",
            "shape on AArch64. An x86-64 shape check can take the place of `(do)`.", "",
            "## Tests", "", "| Test | Category | Family | Note |", "|---|---|---|---|"]
    for name, category, family, note in rows:
        out.append(f"| {name} | {category} | {family} | {note} |")
    with open(os.path.join(TESTS, "X64_STATUS.md"), "w") as handle:
        handle.write("\n".join(out) + "\n")
    print(" ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(" ".join(f"{f}={sum(1 for row in rows if row[2] == f)}" for f in FAMILIES))


if __name__ == "__main__":
    main()
