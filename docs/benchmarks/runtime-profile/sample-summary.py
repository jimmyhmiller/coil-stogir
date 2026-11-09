#!/usr/bin/env python3
"""Summarize macOS sample call trees without counting recursive frames twice.

These are statistical samples, not hardware cycles. Inclusive counts include
callees and must not be summed across functions. Sleeping coordinator frames
are excluded by their terminal wait symbol, not by compiler function names.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('sample', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
text = a.sample.read_text().split('Call graph:\n', 1)[1].split('Total number in stack', 1)[0]
pattern = re.compile(r'^([ +!:|]*)(\d+) (.+?)  \(in (.+?)\)')
stack = []
own, inclusive = Counter(), Counter()
waiting = Counter()
roots = 0
def finish():
    node = stack.pop()
    count = node['count'] - node['children']
    assert count >= 0, node
    symbol = node['symbol']
    if symbol in {'__ulock_wait', '__ulock_wait2', 'mach_msg2_trap',
                  '__psynch_cvwait', 'semaphore_wait_trap'}:
        waiting[symbol] += count
        return
    own[symbol] += count
    for name in {x['symbol'] for x in stack} | {symbol}:
        inclusive[name] += count
for line in text.splitlines():
    m = pattern.match(line)
    if not m:
        continue
    depth, count, symbol = len(m[1]), int(m[2]), m[3]
    while stack and stack[-1]['depth'] >= depth:
        finish()
    if stack:
        stack[-1]['children'] += count
    else:
        roots += count
    stack.append(dict(depth=depth, count=count, children=0, symbol=symbol))
while stack:
    finish()
assert sum(own.values()) + sum(waiting.values()) == roots
result = dict(root_thread_samples=roots, nonwait_samples=sum(own.values()),
              wait_samples=dict(waiting), self_samples=dict(own.most_common()),
              inclusive_samples=dict(inclusive.most_common()),
              qualification='Statistical call-tree samples. Inclusive counts overlap; inlining changes attribution. No hardware-counter interpretation.')
a.output.write_text(json.dumps(result, indent=2) + '\n')
