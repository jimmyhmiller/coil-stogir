#!/usr/bin/env python3
"""Replay baseline, independent blocks, and per-block candidates in an isolated source copy."""
import argparse
import gzip
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('compiler', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--trace', type=Path)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
a.output = a.output.resolve()
a.output.mkdir(parents=True, exist_ok=False)
archive = subprocess.check_output(['git', '-C', str(root), 'archive', '3932dc0', 'src', 'Coil.toml'])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(a.output, filter='data')
shutil.copyfile(Path(__file__).with_name('regional-allocation.coil.in'), a.output/'src/stogir/regional-allocation.coil')
trace = a.trace or root/'docs/benchmarks/loop-load-hoist/induction-primitive.trace.gz'
data = trace.read_bytes()
if trace.suffix == '.gz':
    data = gzip.decompress(data)
(a.output/'primitive.trace').write_bytes(data)
subprocess.run(['python3', str(root/'docs/benchmarks/allocation-regions/replay.py'),
                str(a.output/'primitive.trace'), str(a.output/'replay.coil'), '--regions'], check=True)
s = (a.output/'replay.coil').read_text()
rows = [l.split()[1:] for l in data.decode().splitlines() if l.startswith('ra-snapshot ')]
_, count, mask, _ = map(int, next(r[1:] for r in rows if r[0] == 'begin'))
positions = [int(r[1]) for r in rows if r[0] == 'block']
refs = {int(r[1]): int(r[2]) for r in rows if r[0] == 'node'}
ids = {refs[pos]: i for i, pos in enumerate(positions)}
edges = [tuple(map(int, r[1:])) for r in rows if r[0] == 'edge']
edgeforms = '\n'.join(f'  (push! (mut incoming) (regional/Edge :from {ids[x]} :to {ids[y]}))' for x, y in edges)
s = s.replace('(module allocation.replay)', '(module allocation.replay)\n(import "stogir.regional-allocation" :as regional)')
s = s.replace('       (mut parts)', '       (mut incoming) (ArrayList::new [regional/Edge] allocator)\n       (mut parts)', 1)
s = s.replace('  (match (a/run-shaped-with-tuning!', edgeforms+'\n  (match (regional/run!')
s = s.replace('(slice blocks) (a/Tuning', '(slice blocks) (slice incoming) (a/Tuning')
s = s.replace('  (f/release!', '  (free! (mut incoming))\n  (f/release!')
(a.output/'regional.coil').write_text(s)
s = s.replace('(mut incoming) (ArrayList::new [regional/Edge] allocator)',
              '(mut incoming) (ArrayList::new [regional/Edge] allocator)\n       (mut original) (ArrayList::new [a/Part] allocator)')
s = s.replace('  (match (regional/run!', '  (set! original (regional/clipped parts 0 0x7FFFFFFFFFFFFFFF allocator))\n  (match (a/run-shaped-with-tuning!')
s = s.replace('(slice blocks) (slice incoming) (a/Tuning', '(slice blocks) (a/Tuning')
extra = '''  (for [block 0 (len blocks)]
    (let [span (get blocks block) (mut local) (regional/clipped original (.start span) (.end span) allocator)]
      (for [i 0 (len local)]
        (let [part (elem (mut local) i)]
          (when (>= (.parent part) 0)
            (let [(mut reg) (if (a/covers? (load part) (.start span))
                               (regional/preference parts (.parent part) (cast i32 block) (slice blocks) (slice incoming)) -1)]
              (when (< reg 0)
                (for prior parts
                  (when (and (= (.parent prior) (.parent part))
                             (a/covers? prior (.start (get (.ranges part) 0))))
                    (set! reg (.register prior)))))
              (when (>= reg 0) (set! (.preferred part) reg))))))
      (match (a/run-shaped-with-tuning! (mut local) (mut frame) REGISTER_COUNT REGISTER_MASK (slice shapes)
               (slice moves) [] (a/plain-tuning) allocator)
        (Err [e] (panic "local {}: {}" block e)) (Ok [_] 0))
      (match (check/verify local REGISTER_COUNT REGISTER_MASK) (Err [e] (panic "local {} invalid: {}" block e)) (Ok [_] 0))
      (println "candidate {} {} {}" block (.start span) (.end span))
      (snapshot/parts "candidate" local)
      (regional/release! (mut local))))
  (regional/release! (mut original))
'''.replace('REGISTER_COUNT', str(count)).replace('REGISTER_MASK', str(mask))
pos = s.index('  (for [i 0 (len parts)] (a/release!')
s = s[:pos]+extra+s[pos:]
(a.output/'candidates.coil').write_text(s)
env = {k: v for k, v in os.environ.items() if not k.startswith('COIL_')}
env['COIL_LIBRARY_STATE'] = '0'
for name in ['replay', 'regional', 'candidates']:
    with (a.output/(name+'.log')).open('w') as out:
        subprocess.run([str(a.compiler.resolve()), 'run', name+'.coil', '--backend', 'stogir',
                        '-O3', '--no-debug', '--debug-checks'], cwd=a.output, env=env,
                       stdout=out, stderr=out, check=True)
expected = (a.output/'replay.expected').read_text()
assert (a.output/'replay.log').read_text().startswith(expected), 'baseline replay differs'
(a.output/'result.json').write_text(json.dumps(dict(baseline_exact=True, independent_verified=True,
    candidates_verified=True, blocks=len(positions), trace=str(trace.resolve()), source_commit='3932dc0'), indent=2)+'\n')
print('Exact baseline replay and all candidate allocation checks pass.')
