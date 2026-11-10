#!/usr/bin/env python3
"""Generate and cross-check the x86-64 encoder test (tests/x64-encode.coil).

The case list lives in tools/x86/encode_cases.py: `cases()` returns
(coil-call, assembly, field) triples and `rejections()` returns Coil calls that
must return Err. Expected bytes are never written by hand: every assembly text
is assembled with llvm-mc (x86-64, Intel syntax) and the bytes it produced are
what the test asserts.

  coil-call   an encoder call with `$` standing for the output buffer, e.g.
              "(e/mov-rr $ 64 0 1)"
  assembly    Intel-syntax text; `{L}` is the address of the instruction
              itself, for branch targets ("jmp {L}+5+4096")
  field       the expected Ok value: None for -1; a hex string to locate in the
              assembled bytes (must occur exactly once), e.g. the disp32 of a
              RIP-relative operand; or a negative integer counted from the end
              of the instruction (-4 for a trailing rel32)

Modes:

  gen-encode-cases.py -o tests/x64-encode.coil
      Assemble every case and write the test.

  gen-encode-cases.py --dump-program -o build/x64-encode-dump.coil
      Write a Coil program that prints the bytes the encoder actually produces
      for every case, one "INDEX HEX" line each ("INDEX ERR message" on Err).

  gen-encode-cases.py --check-disasm DUMP
      Second validation. DUMP is that program's output. The encoder's bytes and
      the assembler's bytes are both disassembled with llvm-objdump and the
      texts compared, so an encoding that differs from the assembler's still
      has to decode to the intended instruction. Lists byte-different cases and
      exits non-zero on any case whose disassembly differs.

LLVM tools come from $LLVM_BIN, else `llvm-config-21 --bindir`, else
/opt/homebrew/opt/llvm/bin, else PATH.
"""
import argparse
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

TRIPLE = "x86_64-unknown-linux-gnu"
GROUP = 40


def llvm_bin():
    explicit = os.environ.get("LLVM_BIN")
    if explicit:
        return explicit
    config = shutil.which("llvm-config-21")
    if config:
        return subprocess.check_output([config, "--bindir"], text=True).strip()
    if os.path.exists("/opt/homebrew/opt/llvm/bin/llvm-mc"):
        return "/opt/homebrew/opt/llvm/bin"
    found = shutil.which("llvm-mc")
    if not found:
        sys.exit("gen-encode-cases: llvm-mc not found; set LLVM_BIN")
    return os.path.dirname(found)


def tool(name):
    return os.path.join(llvm_bin(), name)


def run(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        sys.exit("gen-encode-cases: %s failed:\n%s" % (arguments[0], result.stderr))
    return result.stdout


def assemble_object(source, directory, name):
    path = os.path.join(directory, name + ".s")
    obj = os.path.join(directory, name + ".o")
    with open(path, "w") as handle:
        handle.write(source)
    result = subprocess.run(
        [tool("llvm-mc"), "--triple=" + TRIPLE, "-filetype=obj", "-o", obj, path],
        capture_output=True, text=True)
    if result.returncode != 0:
        lines = source.split("\n")
        message = result.stderr
        for match in re.finditer(r"\.s:(\d+):", result.stderr):
            number = int(match.group(1))
            message += "  line %d: %s\n" % (number, lines[number - 1])
        sys.exit("gen-encode-cases: llvm-mc rejected the cases:\n" + message)
    return obj


def assemble(cases):
    """Bytes llvm-mc produces for each case, in order."""
    lines = [".intel_syntax noprefix", ".text"]
    for index, case in enumerate(cases):
        label = "case_%d" % index
        lines.append("%s: %s" % (label, case[1].replace("{L}", label)))
    lines.append("case_%d:" % len(cases))
    with tempfile.TemporaryDirectory() as directory:
        obj = assemble_object("\n".join(lines) + "\n", directory, "cases")
        raw = os.path.join(directory, "cases.bin")
        run([tool("llvm-objcopy"), "-O", "binary", "-j", ".text", obj, raw])
        with open(raw, "rb") as handle:
            text = handle.read()
        addresses = {}
        for line in run([tool("llvm-nm"), obj]).split("\n"):
            parts = line.split()
            if len(parts) == 3 and parts[2].startswith("case_"):
                addresses[int(parts[2][5:])] = int(parts[0], 16)
    if len(addresses) != len(cases) + 1:
        sys.exit("gen-encode-cases: lost case labels in the assembled object")
    return [text[addresses[i]:addresses[i + 1]] for i in range(len(cases))]


def field_offset(case, code):
    field = case[2]
    if field is None:
        return -1
    if isinstance(field, int):
        if field >= 0:
            sys.exit("gen-encode-cases: integer field must be negative: %r" % (case,))
        return len(code) + field
    needle = bytes.fromhex(field)
    first = code.find(needle)
    if first < 0 or code.find(needle, first + 1) >= 0:
        sys.exit("gen-encode-cases: field %s is not unique in %s for %r"
                 % (field, code.hex(), case))
    return first


def call(expression):
    return expression.replace("$", "(mut b)")


HEADER = """;;; GENERATED by tools/x86/gen-encode-cases.py from tools/x86/encode_cases.py.
;;; Do not edit: change the case list and regenerate. Expected bytes are what
;;; llvm-mc assembles for the instruction named beside each case.
(module stogir.tests.x64-encode)
(import "stogir.x64.encode" :as e)
(import "coil.result" :use [Result Ok Err])
(import "coil.arraylist" :use [ArrayList])
(import "coil.alloc" :use [malloc-allocator])

(defn hex-digit [(value u8)] (-> u8)
  (if (< value 10) (+ value #\\0) (+ (- value 10) #\\a)))

(defn same-bytes [(b (ArrayList u8)) (hex (slice u8))] (-> bool)
  (if (!= (* (len b) 2) (len hex))
      false
      (let [(mut same) true
            (mut i) (: 0 i64)]
        (while (< i (len b))
          (let [byte (get b i)]
            (when (or (!= (hex-digit (>> byte 4)) (get hex (* i 2)))
                      (!= (hex-digit (& byte 15)) (get hex (+ (* i 2) 1))))
              (set! same false)))
          (set! i (+ i 1)))
        same)))

(defn print-bytes [(b (ArrayList u8))] (-> void)
  (for byte b (print "{:02x}" byte)))

;;; The encoder call has already appended to `b`. Its bytes must be exactly
;;; `hex` and its Ok value `field`. Leaves `b` empty for the next case.
(defn check [(b (mut (ArrayList u8))) (index i64)
             (result (Result i64 (slice u8))) (hex (slice u8)) (field i64)]
  (-> i64)
  (let [failed
          (match result
            (Ok [actual]
              (if (and (= actual field) (same-bytes b hex))
                  0
                  (do
                    (print "case {}: expected {} field {}, got " index hex field)
                    (print-bytes b)
                    (println " field {}" actual)
                    1)))
            (Err [message]
              (do
                (println "case {}: expected {}, got Err {}" index hex message)
                1)))]
    (clear! (mut b))
    failed))

;;; An invalid operand must return Err and append nothing.
(defn rejected [(b (mut (ArrayList u8))) (index i64)
                (result (Result i64 (slice u8)))] (-> i64)
  (let [failed
          (match result
            (Ok [_]
              (do
                (print "rejection {}: expected Err, got Ok with " index)
                (print-bytes b)
                (println "")
                1))
            (Err [_]
              (if (= (len b) 0)
                  0
                  (do
                    (println "rejection {}: Err but bytes were appended" index)
                    1))))]
    (clear! (mut b))
    failed))
"""


def emit_test(module, output):
    cases = module["cases"]()
    rejections = module["rejections"]()
    codes = assemble(cases)
    out = [HEADER]
    out.append(module.get("EXTRA", "").strip("\n") + "\n")
    groups = []
    for start in range(0, len(cases), GROUP):
        name = "cases-%d" % (start // GROUP)
        groups.append(name)
        out.append("(defn %s [(b (mut (ArrayList u8)))] (-> i64)\n  (+" % name)
        for index in range(start, min(start + GROUP, len(cases))):
            case, code = cases[index], codes[index]
            out.append("\n     ; %s\n     (check (mut b) %d %s \"%s\" %d)"
                       % (case[1], index, call(case[0]), code.hex(),
                          field_offset(case, code)))
        out.append("))\n\n")
    for start in range(0, len(rejections), GROUP):
        name = "rejections-%d" % (start // GROUP)
        groups.append(name)
        out.append("(defn %s [(b (mut (ArrayList u8)))] (-> i64)\n  (+" % name)
        for index in range(start, min(start + GROUP, len(rejections))):
            out.append("\n     (rejected (mut b) %d %s)" % (index, call(rejections[index])))
        out.append("))\n\n")
    if "EXTRA" in module:
        groups.append("extra-checks")
    out.append("(defn main [] (-> i64)\n"
               "  (let [(mut b) (ArrayList::new [u8] (malloc-allocator))\n"
               "        failures\n          (+")
    for name in groups:
        out.append("\n             (%s (mut b))" % name)
    out.append(")]\n"
               "    (free! (mut b))\n"
               "    (println \"x64 encode: %d cases, %d rejections, {} failures\" failures)\n"
               "    (if (= failures 0) 0 1)))\n" % (len(cases), len(rejections)))
    with open(output, "w") as handle:
        handle.write("".join(out))
    print("wrote %s: %d cases, %d rejections" % (output, len(cases), len(rejections)))


DUMP_HEADER = """;;; GENERATED by tools/x86/gen-encode-cases.py --dump-program. Prints the bytes
;;; the encoder produces for each case; feed the output to --check-disasm.
(module stogir.tests.x64-encode-dump)
(import "stogir.x64.encode" :as e)
(import "coil.result" :use [Result Ok Err])
(import "coil.arraylist" :use [ArrayList])
(import "coil.alloc" :use [malloc-allocator])

(defn dump [(b (mut (ArrayList u8))) (index i64) (result (Result i64 (slice u8)))]
  (-> i64)
  (match result
    (Ok [_]
      (do
        (print "{} " index)
        (for byte b (print "{:02x}" byte))
        (println "")))
    (Err [message] (println "{} ERR {}" index message)))
  (clear! (mut b))
  0)
"""


def emit_dump(module, output):
    cases = module["cases"]()
    out = [DUMP_HEADER]
    groups = []
    for start in range(0, len(cases), GROUP):
        name = "cases-%d" % (start // GROUP)
        groups.append(name)
        out.append("\n(defn %s [(b (mut (ArrayList u8)))] (-> i64)\n  (+" % name)
        for index in range(start, min(start + GROUP, len(cases))):
            out.append("\n     (dump (mut b) %d %s)" % (index, call(cases[index][0])))
        out.append("))\n")
    out.append("\n(defn main [] (-> i64)\n"
               "  (let [(mut b) (ArrayList::new [u8] (malloc-allocator))]\n"
               "    (+")
    for name in groups:
        out.append("\n       (%s (mut b))" % name)
    out.append(")))\n")
    with open(output, "w") as handle:
        handle.write("".join(out))
    print("wrote %s: %d cases" % (output, len(cases)))


def disassemble(codes):
    """First instruction llvm-objdump decodes from each byte string.

    Every case sits in its own 32-byte slot, so two layouts of the same cases
    put each one at the same address and branch targets print identically.
    Returns (text, length) pairs.
    """
    lines = [".text"]
    for index, code in enumerate(codes):
        lines.append(".p2align 5, 0xcc")
        lines.append("case_%d:" % index)
        if code:
            lines.append(".byte " + ",".join("0x%02x" % byte for byte in code))
    lines.append(".p2align 5, 0xcc")
    lines.append(".byte 0xcc")
    with tempfile.TemporaryDirectory() as directory:
        obj = assemble_object("\n".join(lines) + "\n", directory, "bytes")
        listing = run([tool("llvm-objdump"), "-d", "-M", "intel",
                       "--no-show-raw-insn", obj])
    result = [("(no bytes)", 0)] * len(codes)
    current = None
    start = None
    for line in listing.split("\n"):
        label = re.match(r"^[0-9a-f]+ <case_(\d+)>:", line)
        if label:
            current = int(label.group(1))
            start = None
            continue
        instruction = re.match(r"^\s*([0-9a-f]+):\s+(.*)$", line)
        if current is None or not instruction:
            continue
        address = int(instruction.group(1), 16)
        if start is None:
            start = address
            text = re.sub(r"\s+", " ", instruction.group(2).split("#")[0]).strip()
            result[current] = (text, None)
        elif result[current][1] is None:
            result[current] = (result[current][0], address - start)
    return result


def check_disasm(module, dump_path):
    cases = module["cases"]()
    reference = assemble(cases)
    actual = [None] * len(cases)
    errors = []
    with open(dump_path) as handle:
        for line in handle:
            parts = line.split(None, 1)
            if not parts or not parts[0].isdigit():
                continue
            index = int(parts[0])
            rest = parts[1].strip() if len(parts) > 1 else ""
            if rest.startswith("ERR"):
                errors.append((index, rest))
                actual[index] = b""
            else:
                actual[index] = bytes.fromhex(rest)
    missing = [i for i, code in enumerate(actual) if code is None]
    if missing:
        sys.exit("gen-encode-cases: dump has no line for cases %s" % missing[:10])
    want = disassemble(reference)
    got = disassemble(actual)
    identical = different = wrong = 0
    for index, case in enumerate(cases):
        if actual[index] == reference[index]:
            identical += 1
            continue
        # The decoded instruction must be the intended one and must consume
        # every byte the encoder produced (no trailing garbage).
        whole = got[index][1] == len(actual[index])
        same = got[index][0] == want[index][0] and whole
        if same:
            different += 1
        else:
            wrong += 1
        print("%s case %d: %s\n    asm      %s\n    llvm-mc  %s  %s\n    encoder  %s  %s"
              % ("DIFFERENT-BYTES" if same else "WRONG", index, case[0], case[1],
                 reference[index].hex(), want[index][0],
                 actual[index].hex(), got[index][0]))
    for index, message in errors:
        print("ERR case %d: %s: %s" % (index, cases[index][0], message))
    print("%d cases: %d byte-identical, %d different bytes but same instruction, "
          "%d wrong" % (len(cases), identical, different, wrong))
    sys.exit(1 if wrong else 0)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cases", default=os.path.join(here, "encode_cases.py"))
    parser.add_argument("-o", "--output")
    parser.add_argument("--dump-program", action="store_true")
    parser.add_argument("--check-disasm", metavar="DUMP")
    arguments = parser.parse_args()
    module = runpy.run_path(arguments.cases)
    if arguments.check_disasm:
        check_disasm(module, arguments.check_disasm)
    elif arguments.dump_program:
        if not arguments.output:
            sys.exit("gen-encode-cases: --dump-program needs -o FILE")
        emit_dump(module, arguments.output)
    else:
        emit_test(module, arguments.output or
                  os.path.join(here, "..", "..", "tests", "x64-encode.coil"))


if __name__ == "__main__":
    main()
