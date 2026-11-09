"""Exact allocation domains and logical transfer costs from a version-2 replay.

This is an offline research model, not an allocator used by the compiler.
Split points are existing allocation cuts and CFG block boundaries only.
"""
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass
class Part:
    parent: int
    allowed: int
    register: int
    slot: int
    ranges: list
    uses: list
    block: int = -1
    origin: int = -1


def parse_parts(path, group='regions'):
    parts = []
    active = False
    for line in Path(path).read_text().splitlines():
        row = line.split()
        if row[:2] == ['ra-snapshot', 'parts']:
            active = row[2] == group
            if active:
                parts = []
        elif active and row[:2] == ['ra-snapshot', 'part']:
            index, parent, mask, reg, slot, *_ = map(int, row[2:])
            assert index == len(parts)
            parts.append(Part(parent, mask, reg, slot, [], []))
        elif active and row[:2] in (['ra-snapshot', 'range'], ['ra-snapshot', 'use']):
            index, *values = map(int, row[2:])
            getattr(parts[index], 'ranges' if row[1] == 'range' else 'uses').append(tuple(values))
    assert parts, f'missing {group} parts'
    return parts


class Model:
    def __init__(self, trace, baseline):
        self.nodes, self.blocks, self.edges, self.aliases = {}, [], [], {}
        self.phis = defaultdict(list)
        for line in Path(trace).read_text().splitlines():
            row = line.split()
            if row[:1] != ['ra-snapshot']:
                continue
            kind = row[1]
            if kind == 'begin':
                version, self.register_count, self.allowed, self.frame_size = map(int, row[2:])
                assert version == 2, 'PHI and coalescing records required'
            elif kind == 'node':
                position, reference, header, x, y, z = map(int, row[2:])
                self.nodes[position] = (reference, header & 255, x, y, z)
            elif kind == 'block':
                self.blocks.append(tuple(map(int, row[2:])))
            elif kind == 'edge':
                self.edges.append(tuple(map(int, row[2:])))
            elif kind == 'alias':
                self.aliases[int(row[2])] = int(row[3])
            elif kind == 'phi':
                self.phis[int(row[2])].append(tuple(map(int, row[3:])))
        self.byref = {self.nodes[block[0]][0]: i for i, block in enumerate(self.blocks)}
        self.node_byref = {node[0]: node for node in self.nodes.values()}
        original = parse_parts(baseline)
        self.parts = []
        for block, (start, end, *_) in enumerate(self.blocks):
            for origin, part in enumerate(original):
                ranges = [(max(start, low), min(end, high)) for low, high in part.ranges
                          if low < end and start < high]
                if ranges:
                    self.parts.append(replace(part, block=block, origin=origin, ranges=ranges,
                                              uses=[u for u in part.uses if start <= u[0] < end]))
        # Preserve coverage per parent and position, including fixed intervals.
        def coverage(parts):
            result = defaultdict(int)
            for part in parts:
                for low, high in part.ranges:
                    for position in range(low, high):
                        result[part.parent, position] += 1
            return result
        assert coverage(original) == coverage(self.parts), 'clipping lost coverage'
        self.table = [dict() for _ in range(self.blocks[-1][1])]
        occupancy = [set() for _ in self.table]
        for index, part in enumerate(self.parts):
            for low, high in part.ranges:
                for position in range(low, high):
                    occupancy[position].add(index)
                    if part.parent >= 0:
                        assert part.parent not in self.table[position], 'overlapping parent children'
                        self.table[position][part.parent] = index
        self.interference = set()
        for items in occupancy:
            ordered = sorted(items)
            self.interference.update((left, right) for n, left in enumerate(ordered) for right in ordered[n+1:])
        self.domains = []
        self.baseline = []
        for part in self.parts:
            # One canonical home per virtual value; negative reservations never spill.
            stack = self.register_count + part.parent
            old = part.register if part.register >= 0 else stack
            if part.parent < 0:
                domain = [part.register]
            else:
                domain = [reg for reg in range(self.register_count) if part.allowed & self.allowed & (1 << reg)]
                fixed = {reg for _, kind, reg in part.uses if kind == 2}
                assert len(fixed) <= 1, 'baseline child has incompatible fixed requirements'
                if fixed:
                    domain = [reg for reg in domain if reg in fixed]
                if not any(kind >= 1 for _, kind, _ in part.uses):
                    domain.append(stack)
            assert old in domain, 'baseline violates domain'
            self.domains.append(domain)
            self.baseline.append(old)
        self.verify(self.baseline)
        self.transfers = []
        for index, (source, destination) in enumerate(self.edges):
            left, right = self.byref[source], self.byref[destination]
            start, end = self.blocks[left][1]-1, self.blocks[right][0]
            excluded = {self.canonical(dst) for _, dst in self.phis[index]}
            pairs = self.ordinary(self.table[start], self.table[end], excluded)
            for src, dst in self.phis[index]:
                pairs.add((self.locate(src, start), self.locate(dst, end)))
            weight = 10 ** min(self.blocks[left][2], self.blocks[right][2])
            for a, b in sorted(pairs):
                self.transfers.append((a, b, weight, 'edge', index))
        for block, (start, end, depth, *_) in enumerate(self.blocks):
            for position in range(start+1, end):
                for a, b in sorted(self.ordinary(self.table[position-1], self.table[position])):
                    self.transfers.append((a, b, 10 ** depth, 'internal', position))

    def canonical(self, value):
        return self.aliases.get(value, value)

    def locate(self, value, position):
        owner = self.canonical(value)
        seen = set()
        while owner > 0 and owner not in self.table[position] and owner not in seen:
            seen.add(owner)
            node = self.node_byref.get(owner)
            if node is None or node[1] not in (36, 68):
                break
            owner = self.canonical(node[2])
        if owner < 0:
            return owner  # constants are negative, parts are nonnegative
        assert owner in self.table[position], f'unresolved value {value} at {position}'
        return self.table[position][owner]

    @staticmethod
    def ordinary(source, destination, excluded=()):
        return {(source[parent], destination[parent]) for parent in source.keys() & destination.keys()
                if parent not in excluded and source[parent] != destination[parent]}

    def location(self, part, assignment):
        return part if part < 0 else assignment[part]

    def verify(self, assignment):
        assert len(assignment) == len(self.parts)
        for value, domain in zip(assignment, self.domains):
            assert value in domain, 'assignment outside legal domain'
        for a, b in self.interference:
            assert assignment[a] >= self.register_count or assignment[b] >= self.register_count or assignment[a] != assignment[b], 'interfering registers'

    def score(self, assignment):
        total = 0
        counts = defaultdict(int)
        # Deduplicate physical copy pairs at each transfer site, as the native
        # parallel copy planner does. Aliases and repeated PHI inputs matter.
        grouped = defaultdict(set)
        for a, b, weight, kind, site in self.transfers:
            x, y = self.location(a, assignment), self.location(b, assignment)
            if x != y:
                grouped[kind, site, weight].add((x, y))
        for (kind, site, weight), pairs in grouped.items():
            for x, y in pairs:
                memory = x >= self.register_count or y >= self.register_count
                counts[kind] += 1
                counts[kind+'_memory'] += int(memory)
                total += weight * (3 if memory else 1)
        return dict(weighted=total, **counts)

    def region(self, header):
        assert 0 <= header < len(self.blocks)
        result = set()
        for block in range(len(self.blocks)):
            current = block
            while current > header:
                parent = self.blocks[current][4]
                assert parent < current, 'RPO dominator order required'
                current = parent
            if current == header:
                result.add(block)
        return result

    def emit_check(self, assignment, path):
        self.verify(assignment)
        # Unique homes retain existing offsets, then allocate new 8-byte homes.
        # This GP-only probe uses a home merely as a verifier identity; native
        # integration must allocate each parent's actual spill shape.
        homes = {p.parent: p.slot for p in self.parts if p.parent >= 0 and p.slot >= 0}
        next_slot = max([self.frame_size, *(slot+8 for slot in homes.values())])
        for part in self.parts:
            if part.parent >= 0 and part.parent not in homes:
                homes[part.parent] = next_slot
                next_slot += 8
        lines = ['(module allocation.oracle-check)', '(import "stogir.allocation" :as a)',
                 '(import "stogir.allocation-check" :as check)', '(import "stogir.interval" :as r)',
                 '(import "stogir.constraints" :as c)', '(import "coil.arraylist" :use [ArrayList])',
                 '(import "coil.alloc" :use [malloc-allocator])', '(import "coil.result" :use [Ok Err])',
                 '(defn main [] (-> i32)', ' (let [allocator (malloc-allocator) (mut parts) (ArrayList::new [a/Part] allocator)]']
        for i, (part, location) in enumerate(zip(self.parts, assignment)):
            reg = location if location < self.register_count else -1
            slot = homes[part.parent] if part.parent >= 0 else -1
            lines.extend([f'  (push! (mut parts) (a/create {part.parent} allocator))',
                          f'  (set! (.allowed (elem (mut parts) {i})) {part.allowed})',
                          f'  (set! (.register (elem (mut parts) {i})) {reg})',
                          f'  (set! (.spill-slot (elem (mut parts) {i})) {slot})'])
            for low, high in part.ranges:
                lines.append(f'  (r/add! (mut (.ranges (elem (mut parts) {i}))) {low} {high})')
            for position, kind, reg in part.uses:
                lines.append(f'  (assert (c/add! (mut (.uses (elem (mut parts) {i}))) {position} {kind} {reg}))')
        lines.extend([f'  (match (check/verify parts {self.register_count} {self.allowed}) (Err [e] (panic "{{}}" e)) (Ok [_] 0))',
                      '  (for [i 0 (len parts)] (a/release! (elem (mut parts) i)))',
                      '  (free! (mut parts)) (println "oracle assignment verified") 0))'])
        Path(path).write_text('\n'.join(lines)+'\n')
