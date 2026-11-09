#!/usr/bin/env python3
"""Emit a diagnostic full-graph fixture for an externally computed assignment.

This is an emission proof, not compiler policy. Every original native child is
checked before applying the candidate's block-local changes. The library's
allocation checker and normal AArch64 emitter then validate the new assignment.
"""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model import Model, parse_parts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('baseline', type=Path)
    p.add_argument('original', type=Path)
    p.add_argument('assignment', type=Path)
    p.add_argument('graph', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--prefix', required=True)
    p.add_argument('--recolor', action='store_true')
    args = p.parse_args()
    assert all(c.isalnum() or c in '/._-' for c in args.prefix)
    model = Model(args.trace, args.baseline)
    parts = parse_parts(args.original, 'recolor' if args.recolor else 'regions')
    assignment = json.loads(args.assignment.read_text())['assignment']
    model.verify(assignment)
    checks = [f'(assert (= (len (.parts assigned)) {len(parts)}))']
    for i, part in enumerate(parts):
        at = f'(get (.parts assigned) {i})'
        for field, value in [('parent', part.parent), ('register', part.register),
                             ('allowed', part.allowed), ('spill-slot', part.slot)]:
            checks.append(f'(assert (= (.{field} {at}) {value}))')
        checks.append(f'(assert (= (len (.ranges {at})) {len(part.ranges)}))')
        for j, (lo, hi) in enumerate(part.ranges):
            checks.append(f'(assert (= (.start (get (.ranges {at}) {j})) {lo}))')
            checks.append(f'(assert (= (.end (get (.ranges {at}) {j})) {hi}))')
    changes = []
    for part, value in zip(model.parts, assignment):
        original = parts[part.origin]
        reg = value if value < model.register_count else -1
        if reg == original.register:
            continue
        assert reg >= 0 or original.slot >= 0, 'fixture cannot create a new typed home'
        start, end, *_ = model.blocks[part.block]
        changes.append(f'(assign! (mut (.parts assigned)) {part.parent} '
                       f'{part.ranges[0][0]} {start} {end} {reg} a)')
    here = Path(__file__).resolve().parent
    driver = (here/'native-driver.coil.in').read_text()
    driver = driver.replace('BASELINE_ASSERTIONS', '\n  '.join(checks))
    driver = driver.replace('REGION_ASSIGNMENTS', '\n  '.join(changes))
    driver = driver.replace('RECOLOR_ENABLED', str(args.recolor).lower())
    driver = driver.replace('OUTPUT_PREFIX', args.prefix)
    graph = args.graph.read_text()
    main = graph[graph.index('(defn main'):graph.index('  (for enabled [false true]')]
    main += ('  (for modified [false true] (run-fixture graph (slice roots) modified a))\n'
             '  (free! (mut roots)) (g/release! (mut graph)) 0))\n')
    args.output.write_text((here/'native-imports.coil.in').read_text()+driver+'\n'+main)
    print(f'{len(checks)} baseline assertions; {len(changes)} block assignments')


if __name__ == '__main__':
    main()
