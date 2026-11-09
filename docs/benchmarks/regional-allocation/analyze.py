#!/usr/bin/env python3
"""Count logical allocation transfers; rank local candidates with a documented proxy cost."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('replay_directory', type=Path)
a = p.parse_args()
root = a.replay_directory
nodes = {}; blocks = []; edges = []; aliases = {}; phis = defaultdict(list); version = 0
for line in (root/'primitive.trace').read_text().splitlines():
    w = line.split()
    if w[:1] != ['ra-snapshot']:
        continue
    tag = w[1]; v = list(map(int, w[2:])) if tag not in ('parts',) else []
    if tag == 'begin': version = v[0]
    elif tag == 'node':
        pos, ref, header, x, y, z = v; nodes[pos] = (ref, header & 255, x, y, z)
    elif tag == 'block': blocks.append(tuple(v))
    elif tag == 'edge': edges.append(tuple(v))
    elif tag == 'alias': aliases[v[0]] = v[1]
    elif tag == 'phi': phis[v[0]].append((v[1], v[2]))
byref = {nodes[b[0]][0]: b for b in blocks}
node_byref = {n[0]: n for n in nodes.values()}

def parse_parts(path):
    groups = {}; label = None; candidate = None
    for line in path.read_text().splitlines():
        w = line.split()
        if not w: continue
        if w[0] == 'candidate': candidate = int(w[1])
        elif w[:2] == ['ra-snapshot', 'parts']:
            label = candidate if w[2] == 'candidate' else w[2]
            groups[label] = []
        elif label is not None and w[:2] == ['ra-snapshot', 'part']:
            index, parent, mask, reg, slot, *_ = map(int, w[2:])
            assert index == len(groups[label])
            groups[label].append(dict(parent=parent, allowed=mask, register=reg, slot=slot, ranges=[], uses=[]))
        elif label is not None and w[:2] in (['ra-snapshot', 'range'], ['ra-snapshot', 'use']):
            v = list(map(int, w[2:])); groups[label][v[0]]['ranges' if w[1] == 'range' else 'uses'].append(tuple(v[1:]))
    return groups

def locations(parts, start=0, end=None):
    if end is None: end = blocks[-1][1]
    out = [{} for _ in range(end-start)]
    for part in parts:
        if part['parent'] < 0: continue
        loc = ('register', part['register']) if part['register'] >= 0 else ('stack', part['slot'])
        for low, high in part['ranges']:
            for t in range(max(low, start), min(high, end)):
                assert part['parent'] not in out[t-start]
                out[t-start][part['parent']] = loc
    return out

def canonical(ref):
    return aliases.get(ref, ref)

def locate(ref, table):
    owner = canonical(ref)
    if owner in table: return table[owner]
    if owner < 0: return ('constant', owner)
    # Word constants and static addresses have no allocated parts. A same-bank
    # view of a literal has a constant recipe; all other missing values fail.
    seen = set()
    while owner > 0 and owner not in seen:
        seen.add(owner)
        node = node_byref.get(owner)
        if node is None or node[1] not in (36, 68): break
        owner = canonical(node[2])
        if owner in table: return table[owner]
    if owner < 0: return ('constant', owner)
    raise ValueError(f'unresolved boundary value {ref} (canonical {canonical(ref)})')

# This is a static proxy, not a cycle prediction: one unit for a register or
# constant move, three for any stack transfer. It excludes parallel-copy cycle
# expansion, instruction selection effects, and callee-saved prologue costs.
def weight(source, destination):
    if source == destination: return 0
    return 3 if 'stack' in (source[0], destination[0]) else 1

def ordinary(source, destination, excluded=()):
    return {(source[parent], destination[parent]) for parent in source.keys() & destination.keys()
            if parent not in excluded and source[parent] != destination[parent]}

def edge_transfers(index, lookup):
    x, y = edges[index]; source = lookup(byref[x][1]-1); destination = lookup(byref[y][0])
    excluded = {canonical(dest) for _, dest in phis[index]}
    result = ordinary(source, destination, excluded)
    for src, dst in phis[index]:
        pair = (locate(src, source), locate(dst, destination))
        if pair[0] != pair[1]: result.add(pair)
    return result

def memory(moves):
    return sum('stack' in (x[0], y[0]) for x, y in moves)

def counts(parts):
    table = locations(parts)
    boundary = [move for i in range(len(edges)) for move in edge_transfers(i, lambda t: table[t])]
    inside = [move for start, end, *_ in blocks for t in range(start+1, end)
              for move in ordinary(table[t-1], table[t])]
    return dict(parts=len(parts), edge_transfers=len(boundary), edge_memory_transfers=memory(boundary),
                internal_transfers=len(inside), internal_memory_transfers=memory(inside))

def region_cost(lookup, block):
    start, end, depth, *_ = blocks[block]; ref = nodes[start][0]
    boundary = sum(sum(weight(x, y) for x, y in edge_transfers(i, lookup)) * 10**min(byref[src][2], byref[dst][2])
                   for i, (src, dst) in enumerate(edges) if ref in (src, dst))
    inside = sum(sum(weight(x, y) for x, y in ordinary(lookup(t-1), lookup(t))) * 10**depth
                 for t in range(start+1, end))
    return boundary+inside

base = parse_parts(root/'replay.log')['regions']
independent = parse_parts(root/'regional.log')['regions']
local = parse_parts(root/'candidates.log')
table = locations(base); improvements = []
for block, parts in local.items():
    if not isinstance(block, int): continue
    start, end, *_ = blocks[block]; candidate = locations(parts, start, end)
    before = region_cost(lambda t: table[t], block)
    after = region_cost(lambda t: candidate[t-start] if start <= t < end else table[t], block)
    if after < before:
        improvements.append(dict(block=block, span=[start, end], before=before, after=after))
# Conservative, whole-block inheritance probe: fixed constraints, lifetime
# holes, local definitions and physical occupancy can all prevent a change.
predecessors = defaultdict(list)
for src, dst in edges: predecessors[dst].append(src)
inheritance = []
for start, end, *_ in blocks:
    ref = nodes[start][0]
    if len(predecessors[ref]) != 1 or nodes[start][1] in (104, 105): continue
    if any(nodes[t][1] == 67 for t in range(start, end, 2)): continue
    source = table[byref[predecessors[ref][0]][1]-1]
    choices = {}
    for i, part in enumerate(base):
        origin = source.get(part['parent'])
        if not origin or origin[0] != 'register' or origin[1] == part['register']: continue
        if not (part['allowed'] >> origin[1] & 1): continue
        if not any(low <= start and end <= high for low, high in part['ranges']): continue
        if any(kind == 2 and reg != origin[1] for t, kind, reg in part['uses'] if start <= t < end): continue
        choices[i] = origin[1]
    while True:
        rejected = {i for i, reg in choices.items()
                    if any(j != i and choices.get(j, part['register']) == reg
                           and any(low < end and start < high for low, high in part['ranges'])
                           for j, part in enumerate(base))}
        if not rejected: break
        for i in rejected: del choices[i]
    for i, reg in choices.items():
        inheritance.append(dict(span=[start, end], parent=base[i]['parent'],
                                previous_register=base[i]['register'], register=reg))
result = dict(trace_version=version, includes_phi_copies=version >= 2,
              inheritance_opportunities=inheritance,
              alias_records=len(aliases), phi_copy_records=sum(map(len, phis.values())),
              baseline=counts(base), independent=counts(independent),
              local_improvements=sorted(improvements, key=lambda r: r['after']-r['before']),
              caveats=['Static transfers, not dynamic counts or cycles.',
                       'Proxy weights: register/constant=1, stack=3, loop depth factor=10.',
                       'Parallel-copy cycles, spill-home store elimination, and prologue costs excluded.'])
(root/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
