#!/usr/bin/env python3
"""Alternate matched compiler hosts; reject failed or unequal output objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('hosts', nargs='+', help='name=/absolute/path/to/compiler')
parser.add_argument('--rounds', type=int, default=3)
args = parser.parse_args()
if args.rounds < 1:
    parser.error('rounds must be positive')
hosts = [x.split('=', 1) for x in args.hosts]
if any(len(x) != 2 for x in hosts) or len({x[0] for x in hosts}) != len(hosts):
    parser.error('hosts must have distinct names and name=path form')
args.output.mkdir(parents=True, exist_ok=False)
env = {k: v for k, v in os.environ.items() if not k.startswith('COIL_')}
env.update(COIL_LIBRARY_STATE='0', COIL_TPDE_SERIAL='1')
rows = []
reference = None
for round_index in range(args.rounds):
    for name, compiler in hosts if round_index % 2 == 0 else reversed(hosts):
        stem = args.output / f'{name}-{round_index + 1}'
        output = stem.with_suffix('.o')
        result = subprocess.run(['/usr/bin/time', '-l', compiler, 'emit-obj',
            'src/compiler/main.coil', '--backend', 'stogir', '-O3', '--no-debug',
            '-o', str(output.resolve())], cwd=args.root, env=env, capture_output=True, text=True)
        stem.with_suffix('.stderr').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stderr[-2000:]}')
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if reference is None:
            reference = digest
        if digest != reference:
            raise RuntimeError(f'{name} emitted a different object')
        cycles = int(re.search(r'(\d+)\s+cycles elapsed', result.stderr)[1])
        instructions = int(re.search(r'(\d+)\s+instructions retired', result.stderr)[1])
        row = dict(host=name, round=round_index + 1, cycles=cycles,
                   instructions=instructions, sha256=digest)
        rows.append(row)
        (args.output / 'results.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(row), flush=True)
for name, _ in hosts:
    values = [x['cycles'] for x in rows if x['host'] == name]
    print(f'{name}: min {min(values)/1e9:.3f}B, median {statistics.median(values)/1e9:.3f}B')
