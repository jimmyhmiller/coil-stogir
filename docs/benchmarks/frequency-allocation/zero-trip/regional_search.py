#!/usr/bin/env python3
"""CFG-derived loop-bypass regions with bounded, solver-free recoloring.

This remains a research model. Its phase check covers this scalar captured
graph; selected multi-output definition legality must come from the native
transfer bridge before using it as compiler policy.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model import Model
from recolor import Recolor
from flow_model import read_probabilities, apply_weights


def bypass_regions(model):
    successors = defaultdict(list)
    for source, target in model.edges:
        successors[model.byref[source]].append(model.byref[target])

    def enters_loop(block, depth):
        seen = set()
        while block not in seen:
            seen.add(block)
            if model.blocks[block][2] > depth:
                return True
            if model.blocks[block][2] < depth or len(successors[block]) != 1:
                return False
            block = successors[block][0]
        return False

    regions = []
    for anchor in range(len(model.blocks)):
        if len(successors[anchor]) != 2:
            continue
        depth = model.blocks[anchor][2]
        a, b = successors[anchor]
        enters_a, enters_b = enters_loop(a, depth), enters_loop(b, depth)
        if enters_a == enters_b:
            continue
        body, bypass = (a, b) if enters_a else (b, a)
        region, pending = {anchor}, [bypass]
        while pending:
            block = pending.pop()
            if block in region or block <= anchor or block == body or model.blocks[block][2] != depth:
                continue
            region.add(block)
            pending.extend(successors[block])
        if len(region) > 1:
            regions.append(region)
    return sorted(regions, key=lambda region: (len(region), min(region)))


class PhaseChecked(Recolor):
    def __init__(self, model, region, initial):
        super().__init__(model, region, initial, free_first=True)
        self.restricted = []
        for a, b, weight, kind, site in model.transfers:
            if kind != 'internal' or site % 2 != 1 or a < 0:
                continue
            ref, opcode, *_ = model.nodes[site-1]
            if opcode in (79, 80) or (opcode not in (36, 68) and model.canonical(ref) == model.parts[b].parent):
                continue
            self.restricted.append((a, b))

    def score(self, plan):
        assignment = self.assignment(plan)
        if any(assignment[a] != assignment[b] and
               not (assignment[a] < self.m.register_count <= assignment[b])
               for a, b in self.restricted):
            return 10**18
        return self.m.score(assignment)['weighted']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('probabilities', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    model = Model(args.trace, args.baseline)
    frequencies, residual = apply_weights(model, read_probabilities(args.probabilities))
    assignment = model.baseline
    regions = bypass_regions(model)
    baseline = model.score(assignment)
    history = []
    started = time.monotonic()
    for region in regions:
        search = PhaseChecked(model, region, assignment)
        steps = search.run(32, 3, 100, 8)
        assignment = search.assignment({})
        history.append(dict(region=sorted(region), steps=steps, visits=search.visits))
    result = dict(assignment=assignment, baseline=baseline, score=model.score(assignment),
                  regions=[sorted(region) for region in regions], history=history,
                  frequencies=frequencies, residual=residual, seconds=time.monotonic()-started,
                  limits=dict(rounds=32, depth=3, visits_per_root=100, changes_per_plan=8))
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    model.emit_check(assignment, args.output.with_suffix('.coil'))
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('assignment', 'history', 'frequencies')}))


if __name__ == '__main__':
    main()
