#!/usr/bin/env python3
"""Build four diagnostic objects from one lossless compiler graph snapshot."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('snapshot', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
data = a.snapshot.read_bytes()
text = (gzip.decompress(data) if a.snapshot.suffix == '.gz' else data).decode()
rows = [line.split()[1:] for line in text.splitlines() if line.startswith('stogir-snapshot ')]
assert sum(row[0] == 'begin' for row in rows) == 1
out = ['(module stogir.strength.replay)']
for module, alias in [('a64.private-leaf', 'private'), ('graph', 'g'), ('node', 'n'),
                      ('strings', 'strings'), ('a64.compile', 'compile'),
                      ('options', 'options'), ('image', 'image'), ('aot.macho', 'macho')]:
    out.append(f'(import "stogir.{module}" :as {alias})')
out += ['(import "coil.fs" :as fs)', '(import "coil.arraylist" :use [ArrayList])',
        '(import "coil.alloc" :use [malloc-allocator])',
        '(import "coil.result" :use [Ok Err Some None])',
        '(defn main [] (-> i32)',
        ' (let [a (malloc-allocator) (mut graph) (g/create a) (mut roots) (ArrayList::new [i32] a)]',
        '  (clear! (mut (.instructions graph))) (clear! (mut (.arities graph)))']
for row in rows:
    kind = row[0]
    values = list(map(int, row[1:])) if kind != 'end' else []
    if kind == 'begin':
        entry, prototype = values
    elif kind == 'root':
        out.append(f'  (push! (mut roots) (: {values[0]} i32))')
    elif kind == 'string':
        sid, count, *payload = values
        assert len(payload) == count
        value = ' '.join(f'(: {x} u8)' for x in payload)
        out.append(f'  (match (strings/intern! (mut (.strings graph)) [{value}]) '
                   f'(Some [id] (assert (= id {sid}))) (None [] (panic "string")))')
    elif kind in ('constant', 'instruction'):
        arity, header, op1, op2, op3 = values
        field, meta = ('constants', 'constant-spans') if kind == 'constant' else ('instructions', 'arities')
        out.append(f'  (push! (mut (.{field} graph)) (n/Node :header (: {header} u32) '
                   f':op1 (: {op1} i32) :op2 (: {op2} i32) :op3 (: {op3} i32)))')
        out.append(f'  (push! (mut (.{meta} graph)) (: {arity} i32))')
out += ['  (match (g/rebuild-constant-index! (mut graph) 8) (Ok [_] 0) (Err [e] (panic "{}" e)))',
        f'  (set! (.function-prototype graph) {prototype})']
for name, strength, hoisting in [('baseline', False, False), ('strength', True, False),
                                  ('hoist', False, True), ('hoist-strength', True, True)]:
    context = '(private/no-context)'
    for flag, enabled in [('loop-evict', True), ('loop-reloads', True), ('predict', True),
                           ('induction', True), ('rotate', True), ('regional', True),
                           ('hoist-loads', hoisting), ('strength', strength)]:
        context = f'(private/with-{flag} {context} {str(enabled).lower()})'
    target = json.dumps(str((a.output / f'{name}.o').resolve()))
    out.append(f'''  (match (compile/image-with-private graph {entry} (slice roots) "_strength_replay"
                         (options/Options :level 3) a {context})
    (Err [e] (panic "{name}: {{}}" e))
    (Ok [code]
      (let [(mut code) code]
        (println "{name} text bytes {{}}" (len (.text code)))
        (match (macho/image-object code a)
          (Err [e] (panic "{{}}" e))
          (Ok [bytes]
            (let [(mut bytes) bytes]
              (match (fs/write-file a {target} (slice bytes))
                (Err [_] (panic "write")) (Ok [_] 0))
              (free! (mut bytes)))))
        (image/release! (mut code)))))''')
out += ['  (free! (mut roots)) (g/release! (mut graph)) 0))']
(a.output / 'replay.coil').write_text('\n'.join(out) + '\n')
(a.output / 'snapshot.json').write_text(json.dumps({
    'path': str(a.snapshot.resolve()), 'sha256': hashlib.sha256(data).hexdigest(),
    'qualification': 'Captured graph code-shape diagnostic; not a runtime benchmark.'
}, indent=2) + '\n')
