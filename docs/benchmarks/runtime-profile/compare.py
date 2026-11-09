#!/usr/bin/env python3
"""Compare estimated instruction mixes from serial block-count diagnostics."""
import argparse
from collections import Counter
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('profile', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
names = ['regional', 'strength', 'hoist-strength']
mix = {n: json.loads((a.profile / n / 'mix.json').read_text()) for n in names}
def total(row):
    return sum(v for k, v in row.items() if not k.startswith('#'))
def roles(functions):
    result = Counter()
    for row in functions.values():
        result.update({k: v for k, v in row.items() if not k.startswith('#')})
    return dict(result)
summary = {n: {'estimated_instructions': sum(map(total, m.values())),
               'roles': roles(m)} for n, m in mix.items()}
(a.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
control = mix['regional']
for name in names[1:]:
    candidate = mix[name]
    rows = []
    for function in set(control) | set(candidate):
        before, after = control.get(function, {}), candidate.get(function, {})
        rows.append(dict(function=function, before=total(before), after=total(after),
                         delta=total(after)-total(before),
                         role_delta={k: after.get(k, 0)-before.get(k, 0)
                                     for k in sorted(set(before) | set(after))
                                     if not k.startswith('#')}))
    rows.sort(key=lambda r: (-r['delta'], r['function']))
    (a.output / (name + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    print(name, 'largest estimated increases:')
    for row in rows[:10]:
        print(f"{row['delta']/1e9:+.3f}B {row['function']}")
