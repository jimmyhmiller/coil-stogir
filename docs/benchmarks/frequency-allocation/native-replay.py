#!/usr/bin/env python3
"""Run the native bounded recolorer on the reproduced original children.

Use reproduce.py first. Its directory supplies primitive.trace, replay.coil and
replay.log. Compile in the current library checkout; no solver is required.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from model import Model, parse_parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler', type=Path)
    parser.add_argument('reproduction', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    m = Model(args.reproduction/'primitive.trace', args.reproduction/'replay.log')
    source = (args.reproduction/'replay.coil').read_text()
    source = source.replace('(import "stogir.allocation"',
        '(import "stogir.allocation-recolor" :as rc)\n(import "stogir.locations" :as loc)\n(import "stogir.allocation"', 1)
    lines = ['  (let [(mut copies) (ArrayList::new [rc/Copy] allocator)',
             '        (mut plan) (ArrayList::new [rc/Change] allocator)]']
    for a, b, weight, kind, site in m.transfers:
        dst = m.parts[b].origin
        if a >= 0 and m.parts[a].origin == dst:
            continue
        src = (f'(rc/allocated {m.parts[a].origin})' if a >= 0 else
               f'(rc/recipe (loc/Location :kind 4 :value {a}))')
        site = site if kind == 'edge' else len(m.edges)+site
        lines.append(f'    (rc/add-copy! (mut copies) {src} {dst} {site} {weight})')
    lines += ['    (assert (= (rc/score parts copies plan) 503298))',
              '    (match (rc/run! (mut parts) (mut frame) (slice shapes) copies 29 536412159 allocator)',
              '      (Err [e] (panic "recolor failed: {}" e)) (Ok [count] (println "recolor changes {}" count)))',
              '    (println "recolor score {}" (rc/score parts copies plan))',
              '    (assert (<= (rc/score parts copies plan) 454018))',
              '    (snapshot/parts "recolor" parts)',
              '    (free! (mut copies)) (free! (mut plan)))']
    marker = '  (for [i 0 (len parts)] (a/release!'
    assert source.count(marker) == 1
    source = source.replace(marker, '\n'.join(lines)+'\n'+marker)
    program = args.output/'replay.coil'
    program.write_text(source)
    log = args.output/'replay.log'
    with log.open('w') as out:
        subprocess.run([str(args.compiler.resolve()), 'run', str(program), '--backend',
                        'stogir', '-O3', '--no-debug', '--debug-checks'],
                       env={**os.environ, 'COIL_LIBRARY_STATE': '0'}, stdout=out,
                       stderr=subprocess.STDOUT, check=True)
    old = parse_parts(args.reproduction/'replay.log')
    new = parse_parts(log, 'recolor')
    assert len(old) == len(new)
    for a, b in zip(old, new):
        assert (a.parent, a.allowed, a.ranges, a.uses) == (b.parent, b.allowed, b.ranges, b.uses)
    assignment = [new[p.origin].register if new[p.origin].register >= 0 else
                  m.register_count + p.parent for p in m.parts]
    m.verify(assignment)
    expected = json.loads((args.reproduction/'recolor-0.json').read_text())
    assert assignment == expected['assignment'], 'native assignment differs from prototype'
    result = dict(baseline=m.score(m.baseline), native=m.score(assignment),
                  original_children=len(old), register_changes=sum(a.register != b.register for a, b in zip(old, new)),
                  home_changes=sum(a.slot != b.slot for a, b in zip(old, new)))
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
