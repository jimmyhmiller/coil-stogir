#!/usr/bin/env python3
"""Measure the fixed workload's IR-to-machine generation under matched settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('root', type=Path)
p.add_argument('compiler', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--rounds', type=int, default=3)
a = p.parse_args()
if a.rounds < 1:
    p.error('rounds must be positive')
a.output.mkdir(parents=True, exist_ok=False)
base = {k: v for k, v in os.environ.items() if not k.startswith('COIL_')}
base.update(COIL_LIBRARY_STATE='0', COIL_TPDE_SERIAL='1', COIL_CODEGEN_TIMINGS='1')
policy = dict(COIL_STOGIR_INLINE='small=80,small-scope=any,hoist=1',
              COIL_STOGIR_LOOP_EVICT='1', COIL_STOGIR_LOOP_RELOAD='1', COIL_STOGIR_PREDICT='1')
configs = [('llvm', 'llvm', {}), ('regions', 'stogir', policy),
           ('facts', 'stogir', dict(policy, COIL_STOGIR_BRANCH_FACTS='1'))]
metadata = dict(compiler=str(a.compiler.resolve()),
    compiler_sha256=hashlib.sha256(a.compiler.read_bytes()).hexdigest(),
    root=str(a.root.resolve()), configs=configs)
(a.output/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
rows = []
digests = {}
for i in range(a.rounds):
    for name, backend, settings in configs if i % 2 == 0 else reversed(configs):
        stem = a.output / f'{name}-{i+1}'
        obj = stem.with_suffix('.o')
        env = dict(base, **settings)
        command = [str(a.compiler.resolve()), 'emit-obj', 'src/compiler/main.coil',
                   '--backend', backend, '-O3', '--no-debug', '-o', str(obj.resolve())]
        result = subprocess.run(command, cwd=a.root, env=env, capture_output=True, text=True)
        stem.with_suffix('.stderr').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stderr[-2000:]}')
        digest = hashlib.sha256(obj.read_bytes()).hexdigest()
        if digest != digests.setdefault(name, digest):
            raise RuntimeError(f'{name} produced nondeterministic object bytes')
        timings = [line.split('\t') for line in result.stderr.splitlines()
                   if line.startswith('coil-codegen\t')]
        if not timings:
            raise RuntimeError(f'{name} missing codegen timings')
        seconds = sum(int(line[3]) for line in timings) / 1e9
        row = dict(name=name, round=i+1, generation_seconds=seconds,
                   object_sha256=digest, command=command)
        rows.append(row)
        (a.output/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
        print(json.dumps(row), flush=True)
for name, _, _ in configs:
    values = [r['generation_seconds'] for r in rows if r['name'] == name]
    print(f'{name}: min {min(values):.3f}s median {statistics.median(values):.3f}s')
