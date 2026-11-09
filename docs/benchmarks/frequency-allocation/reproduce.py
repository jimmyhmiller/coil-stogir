#!/usr/bin/env python3
"""Reproduce exact baseline and solver-free recoloring in an isolated source copy."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('compiler', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--regions', type=int, nargs='+', default=[0, 69])
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
source_commit = 'bca7c4d'
a.output = a.output.resolve()
a.output.mkdir(parents=True, exist_ok=False)
archive = subprocess.check_output(['git', '-C', str(root), 'archive', source_commit, 'src', 'Coil.toml'])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(a.output, filter='data')
trace = root/'docs/benchmarks/regional-allocation/primitive.trace.gz'
(a.output/'primitive.trace').write_bytes(gzip.decompress(trace.read_bytes()))
subprocess.run([sys.executable, str(root/'docs/benchmarks/allocation-regions/replay.py'),
                str(a.output/'primitive.trace'), str(a.output/'replay.coil'), '--regions'], check=True)
env = {key: value for key, value in os.environ.items() if not key.startswith('COIL_')}
env['COIL_LIBRARY_STATE'] = '0'

def native(name):
    with (a.output/(name+'.log')).open('w') as log:
        subprocess.run([str(a.compiler.resolve()), 'run', name+'.coil', '--backend', 'stogir',
                        '-O3', '--no-debug', '--debug-checks'], cwd=a.output, env=env,
                       stdout=log, stderr=log, check=True)

native('replay')
assert (a.output/'replay.log').read_text().startswith((a.output/'replay.expected').read_text()), 'baseline changed'
copied = []
for name in ['model.py', 'recolor.py']:
    destination = a.output/name
    shutil.copy2(Path(__file__).with_name(name), destination)
    copied.append(dict(name=name, sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
results = []
for region in a.regions:
    name = f'recolor-{region}'
    with (a.output/(name+'-search.log')).open('w') as log:
        subprocess.run([sys.executable, 'recolor.py', 'primitive.trace', 'replay.log', name+'.json',
                        '--region', str(region), '--rounds', '32'], cwd=a.output,
                       stdout=log, stderr=log, check=True)
    native(name)
    row = json.loads((a.output/(name+'.json')).read_text())
    row.pop('assignment')
    results.append(row)
metadata = dict(source_commit=subprocess.check_output(['git', '-C', str(root), 'rev-parse', source_commit], text=True).strip(),
                trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                compiler=str(a.compiler.resolve()), compiler_sha256=hashlib.sha256(a.compiler.read_bytes()).hexdigest(),
                python=sys.version, tools=copied, baseline_exact=True, assignments_verified=True, results=results)
(a.output/'result.json').write_text(json.dumps(metadata, indent=2)+'\n')
print('Exact baseline and all recolored assignments pass the library allocation verifier.')
