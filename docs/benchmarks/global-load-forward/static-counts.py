#!/usr/bin/env python3
"""Compare static instruction counts of matching symbols; not runtime estimates."""
import argparse
from collections import Counter
import json
import re
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('before')
p.add_argument('after')
p.add_argument('--objdump', default='llvm-objdump')
a = p.parse_args()


def counts(path):
    text = subprocess.check_output(
        [a.objdump, '-d', '--no-show-raw-insn', path], text=True)
    functions = {}
    current = None
    for line in text.splitlines():
        match = re.match(r'^[0-9a-f]+ <(.+)>:$', line)
        if match:
            current = match[1]
            functions[current] = Counter()
        elif current and re.match(r'^[0-9a-f]+:\s+\S', line):
            functions[current][line.split('\t')[1].split()[0]] += 1
    return functions


before, after = counts(a.before), counts(a.after)
rows = []
for name, old in before.items():
    if name not in after:
        continue
    new = after[name]
    change = sum(new.values()) - sum(old.values())
    loads = sum(n for op, n in new.items() if op.startswith('ld')) - sum(
        n for op, n in old.items() if op.startswith('ld'))
    if change or loads:
        rows.append(dict(function=name, instructions_before=sum(old.values()),
                         instruction_delta=change, load_delta=loads))
rows.sort(key=lambda row: row['instruction_delta'])
print(json.dumps(dict(removed_symbols=sorted(before.keys() - after.keys()),
                      added_symbols=sorted(after.keys() - before.keys()),
                      matching_symbol_changes=rows), indent=2))
