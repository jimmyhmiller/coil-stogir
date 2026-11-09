#!/usr/bin/env python3
"""Generate an exact allocation replay from one ra-snapshot trace."""
from pathlib import Path
import argparse

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('trace', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--regions', action='store_true', help='also replay control-only region inheritance')
a = p.parse_args()
rows = [line.split()[1:] for line in a.trace.read_text().splitlines()
        if line.startswith('ra-snapshot ')]
assert sum(r[0] == 'begin' for r in rows) == 1, 'exactly one allocation required'
assert sum(r[0] == 'end' for r in rows) == 1
begin = next(r for r in rows if r[0] == 'begin')
version, count, mask, frame_size = map(int, begin[1:])
assert version == 1
out = ['(module allocation.replay)']
for mod, alias in [('allocation','a'), ('allocation-check','check'),
                   ('allocation-snapshot','snapshot'), ('allocation-regions','regions'), ('frame','f'),
                   ('split-position','split'), ('interval','r'), ('constraints','c')]:
    out.append(f'(import "stogir.{mod}" :as {alias})')
out += ['(import "coil.arraylist" :use [ArrayList])',
        '(import "coil.alloc" :use [malloc-allocator])',
        '(import "coil.result" :use [Ok Err])',
        '(defn main [] (-> i32)',
        ' (let [allocator (malloc-allocator)',
        '       (mut parts) (ArrayList::new [a/Part] allocator)',
        '       (mut frame) (f/create allocator)',
        '       (mut shapes) (ArrayList::new [a/SpillShape] allocator)',
        '       (mut blocks) (ArrayList::new [split/Block] allocator)',
        '       (mut moves) (ArrayList::new [i64] allocator)]',
        f'  (set! (.size frame) {frame_size})']
expected = []
mode = 'input'
for row in rows:
    kind, *values = row
    if kind == 'parts':
        mode = values[0]
    if mode == 'output':
        if kind != 'end':
            expected.append('ra-snapshot ' + ' '.join(row))
        continue
    if kind in ('begin', 'parts', 'node', 'edge'):
        continue
    v = list(map(int, values))
    if kind == 'tuning':
        pos, late_mask, reload, evict, holes = v
        tuning = f'(a/Tuning :late (a/Late :position {pos} :mask {late_mask}) :loop-reloads {str(bool(reload)).lower()} :loop-evict-mask {evict} :call-holes {str(bool(holes)).lower()})'
    elif kind == 'slot':
        off, size, align = v
        out.append(f'  (push! (mut (.slots frame)) (f/Slot :offset {off} :size {size} :alignment {align}))')
    elif kind in ('parent','local'):
        key, val = v
        field = 'parents' if kind == 'parent' else 'locals'
        out.append(f'  (set! (mut (.{field} frame)) (: {key} i32) (: {val} i64))')
    elif kind == 'shape':
        idx, size, align = v
        out.append(f'  (assert (= (len shapes) {idx}))')
        out.append(f'  (push! (mut shapes) (a/SpillShape :size {size} :alignment {align}))')
    elif kind == 'move':
        out.append(f'  (push! (mut moves) (: {v[0]} i64))')
    elif kind == 'block':
        fields = zip(['start','end','depth','header','idom'],v)
        out.append('  (push! (mut blocks) (split/Block '+ ' '.join(f':{k} {val}' for k,val in fields)+'))')
    elif kind == 'part':
        idx, parent, *fields = v
        out.append(f'  (assert (= (len parts) {idx}))')
        out.append(f'  (push! (mut parts) (a/create {parent} allocator))')
        for key,val in zip(['allowed','register','spill-slot','preferred','hint','hint-owner','last-register'], fields):
            out.append(f'  (set! (.{key} (elem (mut parts) {idx})) {val})')
    elif kind == 'range':
        idx,start,end = v
        out.append(f'  (r/add! (mut (.ranges (elem (mut parts) {idx}))) {start} {end})')
    elif kind == 'use':
        idx,pos,kind,reg = v
        out.append(f'  (assert (c/add! (mut (.uses (elem (mut parts) {idx}))) {pos} {kind} {reg}))')
    else:
        raise ValueError(row)
region_code = []
if a.regions:
    block_rows = [tuple(map(int, r[1:])) for r in rows if r[0] == 'block']
    nodes = {int(r[1]): tuple(map(int, r[2:])) for r in rows if r[0] == 'node'}
    by_ref = {nodes[b[0]][0]: b for b in block_rows}
    predecessors = {}
    for r in rows:
        if r[0] == 'edge':
            predecessors.setdefault(int(r[2]), []).append(int(r[1]))
    region_code += ['  (let [(mut sources) (ArrayList::new [i32] allocator)',
                    '        (mut changes) (ArrayList::new [regions/Change] allocator)',
                    '        (mut changed) (: 0 i32)]',
                    '    (for [i 0 (len shapes)] (push! (mut sources) -1))']
    for ref, block in sorted(by_ref.items()):
        start, end, *_ = block
        pred = predecessors.get(ref, [])
        if end - start != 4 or len(pred) != 1 or pred[0] == ref or nodes[start][1] & 255 in (104, 105):
            continue
        if nodes[end - 2][1] & 255 not in (114, 115):
            continue
        source = by_ref[pred[0]][1] - 1
        region_code.append(f'    (set! changed (+ changed (regions/inherit! (mut parts) {start} {end} {source} (mut sources) (mut changes) allocator)))')
    region_code += ['    (println "regions changed {}" changed)',
                    '    (free! (mut sources)) (free! (mut changes)))',
                    f'  (match (check/verify parts {count} {mask}) (Err [e] (panic "{{}}" e)) (Ok [_] 0))',
                    '  (snapshot/parts "regions" parts)']
out += [f'  (match (a/run-shaped-with-tuning! (mut parts) (mut frame) {count} {mask} (slice shapes) (slice moves) (slice blocks) {tuning} allocator)',
        '    (Err [e] (panic "allocation failed: {}" e)) (Ok [_] 0))',
        f'  (match (check/verify parts {count} {mask})',
        '    (Err [e] (panic "invalid allocation: {}" e)) (Ok [_] 0))',
        '  (snapshot/parts "output" parts)',
        *region_code,
        '  (for [i 0 (len parts)] (a/release! (elem (mut parts) i)))',
        '  (free! (mut parts)) (free! (mut shapes)) (free! (mut blocks)) (free! (mut moves))',
        '  (f/release! (mut frame)) 0))']
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text('\n'.join(out)+'\n')
a.output.with_suffix('.expected').write_text('\n'.join(expected)+'\n')
print(f'{len(rows)} records; wrote {a.output}')
