"""Generate an independent clang-assembled write-effect oracle."""
from pathlib import Path
import json
import re
import subprocess

root = Path.cwd()
out = root / 'build/leaf-effects'
out.mkdir(parents=True, exist_ok=True)
cases = []


def add(assembly, register=None, accept=True):
    cases.append(dict(assembly=assembly, expected=0 if register in (None, 31) else 1 << register,
                      accept=accept and register != 30))


for wide in (False, True):
    bank = 'x' if wide else 'w'
    for register in range(32):
        rd = f'{bank}{register}' if register < 31 else bank + 'zr'
        sp = f'{bank}{register}' if register < 31 else ('sp' if wide else 'wsp')
        for op in ('add', 'sub', 'adds', 'subs'):
            add(f'{op} {rd if op.endswith("s") else sp}, {bank}7, #4095', register)
            add(f'{op} {rd}, {bank}7, {bank}9, lsl #{63 if wide else 31}', register)
        if wide:
            for op in ('add', 'sub'):
                add(f'{op} {sp}, x7, x9, uxtx', register)
        for op in ('and', 'orr', 'eor', 'ands', 'bic', 'orn', 'eon', 'bics'):
            add(f'{op} {rd}, {bank}7, {bank}9, asr #3', register)
        for op in ('and', 'orr', 'eor', 'ands'):
            add(f'{op} {rd if op == "ands" else sp}, {bank}7, #0xff', register)
        for op in ('movz', 'movn', 'movk'):
            add(f'{op} {rd}, #0xabcd, lsl #{48 if wide else 16}', register)
        for op in ('sbfm', 'bfm', 'ubfm'):
            add(f'{op} {rd}, {bank}7, #3, #21', register)
        for op in ('csel', 'csinc', 'csinv', 'csneg'):
            add(f'{op} {rd}, {bank}7, {bank}9, ne', register)
        for op in ('madd', 'msub'):
            add(f'{op} {rd}, {bank}7, {bank}9, {bank}11', register)
        for op in ('udiv', 'sdiv', 'lslv', 'lsrv', 'asrv', 'rorv'):
            add(f'{op} {rd}, {bank}7, {bank}9', register)
        for op in ('rbit', 'rev', 'rev16', 'clz'):
            add(f'{op} {rd}, {bank}7', register)
        for op in ('ldr', 'ldur'):
            add(f'{op} {rd}, [x7, #{16 if op == "ldr" else -16}]', register)
        add(f'ldr {rd}, [x7, x9, lsl #{3 if wide else 2}]', register)
        for op in ('str', 'stur'):
            # Store source register does not become a destination, including LR.
            add(f'{op} {rd}, [x7, #{16 if op == "str" else -16}]')
        for op in ('ldrsb', 'ldrsh'):
            add(f'{op} {rd}, [x7, #0]', register)
        if wide:
            add(f'ldrsw {rd}, [x7, #4]', register)
    # Deliberately unsupported forms, whose effects cannot borrow a broad mask.
    for assembly in (f'ldr {bank}3, [x7], #8', f'ldr {bank}3, [x7, #8]!',
                     f'ldp {bank}3, {bank}5, [x7]', f'ror {bank}3, {bank}7, #3'):
        add(assembly, accept=False)
for assembly in ('blr x3', 'br x3', 'ret x3', 'ret', 'bl .', 'b .', 'nop',
                 'mrs x3, nzcv', 'fmov x3, d7', 'ldr d3, [x7]', 'ldr q3, [x7]',
                 'prfm pldl1keep, [x7]', 'svc #0', 'brk #0'):
    add(assembly, accept=False)

assembly = out / 'oracle.s'
assembly.write_text('.text\n.globl _oracle\n_oracle:\n' +
                    '\n'.join('  ' + row['assembly'] for row in cases) + '\n')
subprocess.run(['clang', '-target', 'arm64-apple-macos', '-c', assembly,
                '-o', out / 'oracle.o'], check=True)
text = subprocess.check_output(['/opt/homebrew/opt/llvm/bin/llvm-objdump', '-d',
                                str(out / 'oracle.o')], text=True)
words = [int(match[1], 16) for line in text.splitlines()
         if (match := re.match(r'\s*[0-9a-f]+:\s+([0-9a-f]{8})\s', line))]
assert len(words) == len(cases), (len(words), len(cases))
for row, word in zip(cases, words):
    row['word'] = word
(out / 'oracle.json').write_text(json.dumps(cases, indent=2) + '\n')
checks = '\n'.join('  (check (: {} u32) (: {} u64) {})'.format(
    row['word'], row['expected'], str(row['accept']).lower()) for row in cases)
template = (root / 'tests/leaf-register-effects.coil.in').read_text()
(out / 'validation.coil').write_text(template.replace('  ; ASSEMBLED-CASES', checks))
print(len(cases), 'independent assembler cases')
