"""Inspect static call opportunities; this does not produce clobber certificates."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess


def inspect(obj, objdump, nm):
    disassembly = subprocess.check_output(
        [objdump, '--disassemble', '--reloc', '--no-show-raw-insn', str(obj)], text=True)
    symbols = subprocess.check_output([nm, '-m', str(obj)], text=True)
    private = {line.split()[-1] for line in symbols.splitlines()
               if '(__TEXT,__text) non-external ' in line}
    functions = {}
    current = None
    last_instruction = None
    for line in disassembly.splitlines():
        label = re.fullmatch(r'([0-9a-f]+) <([^>]+)>:', line)
        if label:
            current = dict(name=label[2], start=int(label[1], 16), instructions=[],
                           relocations=[], mentioned=set(), calls=[])
            functions[label[2]] = current
            last_instruction = None
            continue
        if current is None:
            continue
        relocation = re.fullmatch(r'\s*([0-9a-f]+):\s+(ARM64_RELOC_\w+)\s+(\S+)\s*', line)
        if relocation:
            address, kind, target = relocation.groups()
            address = int(address, 16)
            current['relocations'].append((address, kind, target))
            if kind == 'ARM64_RELOC_BRANCH26':
                assert last_instruction and last_instruction[0] == address
                assert last_instruction[1] in ('bl', 'b')
                if last_instruction[1] == 'bl':
                    current['calls'].append(target)
            continue
        instruction = re.fullmatch(r'\s*([0-9a-f]+):\s+([a-z][a-z0-9.]*)\s*(.*)', line)
        if instruction:
            address, opcode, operands = instruction.groups()
            last_instruction = (int(address, 16), opcode, operands)
            current['instructions'].append(last_instruction)
            current['mentioned'].update(int(x) for x in re.findall(r'\b[wx](\d+)\b', operands))
    calls = collections.Counter()
    callers = collections.defaultdict(set)
    for function in functions.values():
        for target in function['calls']:
            calls[target] += 1
            callers[target].add(function['name'])
    candidates = []
    for name, function in functions.items():
        instructions = function['instructions']
        if name not in private or not instructions or not calls[name]:
            continue
        # A relocation may denote a tail transfer or literal/data access. Decline
        # all of them here; a production proof must account for their exact effects.
        if function['relocations']:
            continue
        if any(op in ('bl', 'blr', 'br', 'eret', 'svc', 'hvc', 'smc', 'brk', 'hlt')
               for _, op, _ in instructions):
            continue
        start, end = function['start'], instructions[-1][0] + 4
        local_branches = True
        for address, op, operands in instructions:
            if op == 'b' or op.startswith('b.') or op in ('cbz', 'cbnz', 'tbz', 'tbnz'):
                target = re.search(r'0x([0-9a-f]+)', operands)
                if not target or not start <= int(target[1], 16) < end:
                    local_branches = False
        if not local_branches:
            continue
        unmentioned = [register for register in range(16)
                       if register not in function['mentioned']]
        if not unmentioned:
            continue
        candidates.append(dict(name=name, static_direct_calls=calls[name],
                               distinct_callers=len(callers[name]),
                               instruction_count=len(instructions),
                               mentioned_gpr=sorted(function['mentioned']),
                               unmentioned_volatile_gpr=unmentioned,
                               opcodes=sorted({op for _, op, _ in instructions})))
    candidates.sort(key=lambda row: (-row['static_direct_calls'], row['name']))
    return dict(qualification=(
        'Opportunity audit only. Static register mentions are not machine write '
        'effects or an ABI certificate. No argument/result marshalling proof, '
        'implicit-effect decoding, dynamic call frequencies, measured savings, '
        'or clobber-mask relaxation is implied. Relocations, explicit calls, '
        'indirect/tail transfers and external branches decline.'),
        object=str(obj.resolve()), object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
        functions=len(functions), private_functions=len(private),
        candidates=len(candidates), candidate_call_sites=sum(
            row['static_direct_calls'] for row in candidates), rows=candidates)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('object', type=Path)
    parser.add_argument('--objdump', default='/opt/homebrew/opt/llvm/bin/llvm-objdump')
    parser.add_argument('--nm', default='/opt/homebrew/opt/llvm/bin/llvm-nm')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.object, args.objdump, args.nm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, indent=2))
