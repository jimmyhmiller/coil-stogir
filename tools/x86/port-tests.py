#!/usr/bin/env python3
"""Port facade-level tests from the AArch64 backend modules to the target-neutral
facade, so the same files gate the x86-64 backend.

    tools/x86/port-tests.py            port every portable test in tests/
    tools/x86/port-tests.py --list     print what would be ported, and why not

A test is portable when the only `stogir.a64.*` modules it imports are
`compile` and `private-leaf`, it is not in EXCLUDED, and every function it
defines as AArch64 machine code has an x86-64 alternative (the two definitions
are the arms of a top-level `target/arch-pick`; the x86-64 bytes come from
tools/x86/asm-bytes.sh). A ported file no
longer imports `stogir.a64.*`, so running the script again changes nothing.

What a port does:
  1. imports: stogir.a64.compile -> stogir.native.compile,
     stogir.a64.private-leaf -> stogir.native.private-leaf,
     stogir.jit.darwin -> stogir.jit.native,
     stogir.aot.macho (image-object) -> stogir.aot.native;
  2. in a test that writes an object file, every "_name" symbol literal becomes
     (target/os-pick "_name" "name"): the object's symbols are C linker names,
     which have no underscore on ELF. Symbols of JIT-only tests are internal to
     their image and stay as written;
  3. GUARDS: statements that assert AArch64 instruction shapes are wrapped in
     (target/arch-pick STATEMENT (do)), so they run unchanged on AArch64 and the
     behavioral part of the test runs everywhere;
  4. REWRITES: literal one-off edits.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS = os.path.join(ROOT, "tests")

# Importing only compile/private-leaf, but built on AArch64 machine code.
EXCLUDED = {
    "global-alignment": "fixtures are hand-encoded AArch64 words (RET, ADRP/ADD patches) and decode ADRP",
    "jit-hva-varargs": "calls a hand-encoded AArch64 probe function",
    "private-leaf": "registers hand-encoded AArch64 leaves and checks their register masks",
    "x64-core-entry": "x86-64 backend test; borrows the private-leaf context types",
}

# A probe function written as AArch64 bytes does not compile for another
# machine, unless the test also carries its x86-64 bytes.
MACHINE_CODE = re.compile(r"machine-code\s+\(Aarch64\)")
MACHINE_CODE_X64 = re.compile(r"machine-code\s+\(X86_64\)")
MACHINE_CODE_REASON = "calls a probe function written as AArch64 machine code"


def machine_code_only_a64(text):
    return (len(MACHINE_CODE.findall(text)) > len(MACHINE_CODE_X64.findall(text)))

# file -> [(text the statement starts with, which occurrence or None for all,
#           x86-64 replacement)]
GUARDS = {
    "extension-idioms": [("(assert (= (words built ", None, "(do)")],
    "forwarded-return-tail": [("(for [i 0 words]", None, "(do)")],
    "frame-direct-access": [("(for [i 0 (/ (len text) 4)]", None, "(do)"),
                            ("(assert (> direct 0))", None, "(do)"),
                            ("(assert (> zeroes 0))", None, "(do)")],
    "jit-bit-test": [("(let [branches (words (slice text) 0)", None, "(do)"),
                     ("(when (or (!= down (if shifted groups 0))", None, "(do)")],
    "jit-condition-merge": [("(when (and (= kind 1) (!= merged 0))", None, "(do)"),
                            ("(when (and (!= kind 1) (< (.merged tally) 100))", None, "(do)")],
    "jit-condition-merge-zero": [("(when (and (= merged 0) (or (= shape 0) (< test 4)))", None, "(do)")],
    "jit-equality-chain": [("(if (and (or (and (= shifts 1) (= downward 0))", None, "0")],
    "jit-literal-operands": [("(when (!= (= moves 0) scratch-free)", None, "(do)"),
                             ("(when (or (!= (words (slice text) 0) 0) (!= (words (slice text) 1) 0))", None, "(do)")],
    "jit-loop": [("(when (!= (% (+ (* i 4) displacement) 8) 0)", None, "(do)"),
                 ("(when (or (!= backwards 1) (!= unconditional 0))", None, "(do)")],
    "jit-multiply-literal": [("(when (and (not simple)", None, "(do)")],
    "jit-reciprocal-division": [("(while (< (+ at 3) (len code))", None, "(do)")],
    "jit-return-tail": [("(let [(mut at) (: 0 i64)]", None, "(do)")],
    "jit-select-diamond": [("(when (and (or (<= variant 4) (= variant 8)) (or (!= jumps 0)", None, "(do)"),
                           ("(when (and (>= variant 5) (<= variant 7) (= jumps 0))", None, "(do)")],
    "jit-select-dispatch": [("(when (and convert (or (!= jumps 0)", None, "(do)"),
                            ("(when (and (not convert) (= jumps 0))", None, "(do)")],
    "jit-select-floating": [("(when (and (<= variant 4)", None, "(do)"),
                            ("(when (and (>= variant 5) (= jumps 0))", None, "(do)")],
    "jit-subsumed-guard": [("(when (and passes (if folds (> found 1) (< found 2)))", None, "(do)")],
    "jit-switch-direct": [("(let [(mut at) (: 0 i64)]", None, "(do)")],
    "jit-termination": [("(when (or (!= traps (if (= mode 3) 2 1))", None, "(do)")],
    "jit-zero-branch": [("(when (and zero-form (or (!= zero-tests 1)", None, "(do)"),
                        ("(when (and sign-form (or (!= sign-tests 1)", None, "(do)"),
                        ("(when (and zero-key (or (= ty 5) (= ty 4))", None, "(do)"),
                        ("(when (if (and (> shape 0) (<= amount 4095))", None, "(do)"),
                        ("(when (!= (flag-decrements text) 1)", None, "(do)")],
    "loop-carried-update-order": [("(when (!= (register-moves bytes) moves)", None, "(do)")],
    "narrow-truth-test": [("(if from-parameter", 0, "(do)")],
    "rotated-test-block": [("(for [k 0 (/ (len text) 4)]", None, "(do)")],
    "sext-load": [("(for [i 0 (/ (len text) 4)] (assert (not (sign-extend?", None, "(do)")],
    "shrink-wrap": [("(when (and shrink (!= shape 1) (frame-entry? word))", None, "(do)"),
                    ("(let [faults (frame-faults code \"_sw_entry\")]", None, "(do)"),
                    ("(when (and (not shrink) (not (frame-entry? word)))", None, "(do)")],
    "tail-split": [("(when (!= (links (.text code)) 0)", None, "(do)")],
    "trunc-view-coalesce": [("(for [i 0 (/ (len text) 4)] (assert (not (word-move?", None, "(do)")],
    "volatile-access": [("(check-census shape (census (.text code)))", None, "(do)")],
    "zext-known-zero": [("(if parameter-arm (assert (> extensions 0)) (assert (= extensions 0)))", None, "(do)"),
                        ("(for [i 0 (/ (len text) 4)] (assert (not (zero-extend?", None, "(do)")],
}

# Numbers that differ between the systems rather than the machines.
TRAP_SIGNAL = ("(signal 5", "(signal (target/arch-pick 5 4)")
BUS_SIGNAL = ("(signal 10 handler)", "(signal (target/os-pick 10 7) handler)", 1)
ANONYMOUS_MAPPING = (" 0x1002 -1 0)", " (target/os-pick 0x1002 0x22) -1 0)", 2)

# The calling-convention number of a prototype: 9 is AArch64 Darwin, 8 System V.
CONVENTION = ("(calls/create 9 5 ", "(calls/create (target/arch-pick 9 8) 5 ")

# file -> [(old, new, expected count)]
REWRITES = {
    # A never-executed prefix image: one return and padding to 5004 bytes.
    "module-execution": [
        ("(bytes/append32! (mut (.text prefix)) 0xD65F03C0)",
         "(bytes/append32! (mut (.text prefix)) (target/arch-pick 0xD65F03C0 0x909090C3))", 1),
        ("(bytes/append32! (mut (.text prefix)) 0xD503201F)",
         "(bytes/append32! (mut (.text prefix)) (target/arch-pick 0xD503201F 0x90909090))", 1),
        TRAP_SIGNAL + (2,),
    ],
    # The trap instruction raises SIGTRAP (BRK) on AArch64 and SIGILL (UD2) on x86-64.
    "jit-termination": [TRAP_SIGNAL + (1,)],
    "jit-stack-invalid": [TRAP_SIGNAL + (1,)],
    "jit-bulk": [BUS_SIGNAL, ANONYMOUS_MAPPING],
    "jit-bulk-pairs": [ANONYMOUS_MAPPING],
    "jit-vector-transport": [BUS_SIGNAL, ANONYMOUS_MAPPING, CONVENTION + (2,)],
    "jit-vector-arithmetic": [CONVENTION + (1,)],
    "jit-vector-constants": [CONVENTION + (2,)],
    "jit-vector-locals": [CONVENTION + (2,)],
    "jit-vector-unary": [CONVENTION + (1,)],
    "jit-bulk-pressure": [CONVENTION + (1,)],
}

IMPORTS = [
    ('"stogir.a64.compile"', '"stogir.native.compile"'),
    ('"stogir.a64.private-leaf"', '"stogir.native.private-leaf"'),
    ('"stogir.jit.darwin"', '"stogir.jit.native"'),
]

A64_IMPORT = re.compile(r'"stogir\.a64\.([a-z0-9-]+)"')
SYMBOL = re.compile(r'(?<![A-Za-z0-9_\\])"_([A-Za-z][A-Za-z0-9_]*)"')


def form_end(text, start):
    """Index just past the s-expression that starts at text[start] == '('."""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif c == "#" and text[i + 1] == "\\":
            i += 3
            while i < n and (text[i].isalnum() or text[i] == "-"):
                i += 1
            continue
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced form")


def guard(name, text):
    for anchor, which, other in GUARDS.get(name, []):
        starts = []
        for match in re.finditer(r"^[ \t]*" + re.escape(anchor), text, re.M):
            starts.append(match.end() - len(anchor))
        if not starts:
            raise SystemExit(f"{name}: guard anchor not found: {anchor}")
        if which is not None:
            starts = [starts[which]]
        for start in reversed(starts):
            end = form_end(text, start)
            text = (text[:start] + "(target/arch-pick " + text[start:end] + " " + other + ")"
                    + text[end:])
    return text


def writes_object(text):
    return ("compile/object" in text or "macho/image-object" in text
            or "aot/image-object" in text)


def c_symbols(text):
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("(extern") or stripped.startswith(";"):
            lines.append(line)
        else:
            lines.append(SYMBOL.sub(lambda m: f'(target/os-pick "_{m.group(1)}" "{m.group(1)}")', line))
    return "\n".join(lines)


def classify(text):
    return sorted(set(A64_IMPORT.findall(text)))


def port(name, text):
    for old, new in IMPORTS:
        text = text.replace(old, new)
    if '"stogir.aot.macho"' in text:
        if re.search(r"\baot/", text) or "macho/text-object" in text:
            raise SystemExit(f"{name}: unexpected object-writer use")
        text = text.replace('"stogir.aot.macho" :as macho', '"stogir.aot.native" :as aot')
        text = text.replace("macho/image-object", "aot/image-object")
        if "macho/" in text or '"stogir.aot.macho"' in text:
            raise SystemExit(f"{name}: Mach-O use left behind")
    if writes_object(text):
        text = c_symbols(text)
    text = guard(name, text)
    for old, new, count in REWRITES.get(name, []):
        if text.count(old) != count:
            raise SystemExit(f"{name}: expected {count} of: {old}")
        text = text.replace(old, new)
    if "target/" in text:
        if re.search(r":as target\b", text):
            raise SystemExit(f"{name}: alias `target` is taken")
        first = re.search(r'^\(import "stogir\.[^\n]*\n', text, re.M)
        text = text[:first.end()] + '(import "stogir.target" :as target)\n' + text[first.end():]
    return text


def main():
    listing = "--list" in sys.argv
    ported = 0
    for entry in sorted(os.listdir(TESTS)):
        if not entry.endswith(".coil"):
            continue
        name = entry[:-5]
        # Tests of x86-64 internals name backend modules on purpose.
        if name.startswith("x64-"):
            continue
        path = os.path.join(TESTS, entry)
        with open(path) as handle:
            text = handle.read()
        used = classify(text)
        if not used:
            continue
        internal = [m for m in used if m not in ("compile", "private-leaf")]
        if internal:
            if listing:
                print(f"a64-internal {name}: imports {' '.join(internal)}")
            continue
        if name in EXCLUDED or machine_code_only_a64(text):
            if listing:
                print(f"a64-internal {name}: {EXCLUDED.get(name, MACHINE_CODE_REASON)}")
            continue
        if re.search(r"\bcompile/generate", text):
            raise SystemExit(f"{name}: uses a backend-internal compile entry")
        ported += 1
        if listing:
            print(f"port {name}")
            continue
        with open(path, "w") as handle:
            handle.write(port(name, text))
    print(f"{ported} tests {'to port' if listing else 'ported'}", file=sys.stderr)


if __name__ == "__main__":
    main()
