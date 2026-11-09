#!/usr/bin/env python3
"""Bounded regional ejection chains, scored over complete CFG transfer boundaries.

Research prototype: no solver, no captured profile weights, no function-specific
rules. A transaction must preserve all allocation constraints and strictly
reduce the documented logical transfer proxy before it is retained.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
from model import Model


class Recolor:
    def __init__(self, model, region, initial):
        self.m = model
        keys = {}
        self.members, self.domains, self.current, self.groupof = [], [], [], []
        for i, (part, domain, old) in enumerate(zip(model.parts, model.domains, initial)):
            key = ('inside', part.origin) if part.block in region else ('outside', i)
            domain = set(domain) if part.block in region else {old}
            if key not in keys:
                keys[key] = len(self.members)
                self.members.append([])
                self.domains.append(domain)
                self.current.append(old)
            group = keys[key]
            assert self.current[group] == old, 'whole child has different incoming locations'
            self.members[group].append(i)
            self.domains[group] &= domain
            self.groupof.append(group)
        self.neighbors = [set() for _ in self.members]
        for a, b in model.interference:
            left, right = self.groupof[a], self.groupof[b]
            assert left != right, 'overlapping pieces grouped together'
            self.neighbors[left].add(right)
            self.neighbors[right].add(left)
        # Fixed reservations and mandatory assignments remove colors before
        # search, including call clobbers and fixed argument/result registers.
        changed = True
        while changed:
            changed = False
            for group, domain in enumerate(self.domains):
                occupied = {next(iter(self.domains[n])) for n in self.neighbors[group]
                            if len(self.domains[n]) == 1}
                new = {v for v in domain if v >= model.register_count or v not in occupied}
                assert self.current[group] in new, 'baseline removed by domain propagation'
                if new != domain:
                    self.domains[group] = new
                    changed = True
        self.links = [set() for _ in self.members]
        for a, b, *_ in model.transfers:
            if a >= 0 and b >= 0:
                x, y = self.groupof[a], self.groupof[b]
                if x != y:
                    self.links[x].add(y)
                    self.links[y].add(x)
        self.visits = 0

    def assignment(self, plan):
        return [plan.get(group, self.current[group]) for group in self.groupof]

    def score(self, plan):
        return self.m.score(self.assignment(plan))['weighted']

    def place(self, group, location, plan, depth, limit, max_changes):
        self.visits += 1
        if self.visits > limit or location not in self.domains[group]:
            return
        if group in plan:
            if plan[group] == location:
                yield plan
            return
        if len(plan) >= max_changes:
            return
        plan = dict(plan)
        plan[group] = location
        if location >= self.m.register_count:
            yield plan
            return
        conflicts = sorted(n for n in self.neighbors[group]
                           if plan.get(n, self.current[n]) == location)
        if not conflicts:
            yield plan
            return
        if depth <= 0:
            return

        def resolve(index, proposed):
            if index == len(conflicts):
                yield proposed
                return
            victim = conflicts[index]
            if proposed.get(victim, self.current[victim]) != location:
                yield from resolve(index+1, proposed)
                return
            if victim in proposed:
                return
            alternatives = []
            for alternative in self.domains[victim]:
                if alternative != location:
                    attempt = dict(proposed)
                    attempt[victim] = alternative
                    alternatives.append((self.score(attempt), alternative))
            for _, alternative in sorted(alternatives):
                if self.visits >= limit:
                    break
                for solved in self.place(victim, alternative, proposed, depth-1, limit, max_changes):
                    yield from resolve(index+1, solved)
        yield from resolve(0, plan)

    def run(self, rounds, depth, budget, max_changes):
        history = []
        self.no_improving_transaction = False
        for iteration in range(rounds):
            before = self.score({})
            best_score, best = before, None
            candidates = set()
            # A root move aims to remove an actual transfer. Displaced owners
            # may use any legal color or spill home, so chains can free it.
            for group, domain in enumerate(self.domains):
                if len(domain) <= 1:
                    continue
                for neighbor in self.links[group]:
                    desired = self.current[neighbor]
                    if desired != self.current[group] and desired in domain:
                        candidates.add((group, desired))
            ranked = sorted((self.score({group: desired}), group, desired) for group, desired in candidates)
            for _, group, desired in ranked:
                limit = self.visits+budget
                for plan in self.place(group, desired, {}, depth, limit, max_changes):
                    score = self.score(plan)
                    if score < best_score or (score == best_score and best is not None and len(plan) < len(best)):
                        assignment = self.assignment(plan)
                        self.m.verify(assignment)
                        best_score, best = score, plan
            if best is None:
                self.no_improving_transaction = True
                break
            changes = []
            for group, location in best.items():
                if location != self.current[group]:
                    part = self.m.parts[self.members[group][0]]
                    changes.append(dict(parent=part.parent, origin=part.origin,
                                        old=self.current[group], new=location))
                self.current[group] = location
            self.m.verify(self.assignment({}))
            history.append(dict(iteration=iteration+1, before=before, after=best_score, changes=changes))
            print(json.dumps(history[-1]), flush=True)
        return history


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('baseline', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--region', type=int, required=True)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--depth', type=int, default=3)
    p.add_argument('--budget', type=int, default=100)
    p.add_argument('--max-changes', type=int, default=8)
    a = p.parse_args()
    assert min(a.rounds, a.depth, a.budget, a.max_changes) > 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    m = Model(a.trace, a.baseline)
    r = Recolor(m, m.region(a.region), m.baseline)
    started = time.monotonic()
    history = r.run(a.rounds, a.depth, a.budget, a.max_changes)
    assignment = r.assignment({})
    m.verify(assignment)
    result = dict(region=a.region, baseline=m.score(m.baseline), candidate=m.score(assignment),
                  history=history, assignment=assignment, visits=r.visits,
                  seconds=time.monotonic()-started,
                  no_improving_transaction_within_limits=r.no_improving_transaction,
                  limits=dict(rounds=a.rounds, depth=a.depth, budget=a.budget, max_changes=a.max_changes))
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    m.emit_check(assignment, a.output.with_suffix('.coil'))
    print(json.dumps({k:v for k,v in result.items() if k not in ('assignment', 'history')}), flush=True)


if __name__ == '__main__':
    main()
