#!/usr/bin/env python3
"""Run linked consumers using a manifest of freshly generated object fixtures."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('compiler', type=Path)
p.add_argument('manifest', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--newer-than', type=int, required=True)
a = p.parse_args()
m = json.loads(a.manifest.read_text())
a.output.mkdir(parents=True, exist_ok=False)
fixtures = Path(tempfile.mkdtemp(prefix='stogir-link-'))
originals = sorted(set(f for values in m.values() for f in values))
records = {}
for filename in originals:
    source = Path(filename)
    if source.stat().st_mtime < a.newer_than:
        raise RuntimeError(f'stale fixture: {source}')
    target = fixtures / source.name
    if target.exists():
        raise RuntimeError(f'duplicate fixture basename: {source}')
    shutil.copy2(source, target)
    records[filename] = dict(copy=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(a.output/'fixtures.json').write_text(json.dumps(records, indent=2)+'\n')
env = {k:v for k,v in os.environ.items() if not k.startswith('COIL_')}
env['COIL_LIBRARY_STATE'] = '0'
def run(item):
    name, files = item
    if not files:
        raise RuntimeError(f'no fixtures for {name}')
    cmd = [str(a.compiler.resolve()), 'run', f'tests/{name}.coil', '--backend',
           'stogir', '-O3', '--no-debug', '--debug-checks']
    for filename in files:
        cmd.extend(['--link-flag', records[filename]['copy']])
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    (a.output/f'{name}.log').write_text(proc.stdout+proc.stderr)
    result = dict(test=name, returncode=proc.returncode, objects=len(files))
    print(json.dumps(result), flush=True)
    return result
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(run, sorted(m.items())))
(a.output/'results.json').write_text(json.dumps(results, indent=2)+'\n')
raise SystemExit(int(any(x['returncode'] for x in results)))
