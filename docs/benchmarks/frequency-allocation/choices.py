#!/usr/bin/env python3
"""Offline finite register-choice MaxSAT search with exact boundary constraints."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
import z3
from model import Model

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('trace', type=Path)
p.add_argument('baseline', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--region', type=int, required=True)
p.add_argument('--seconds', type=int, default=45)
p.add_argument('--registers', type=int, nargs='+')
p.add_argument('--whole-parts', action='store_true')
a = p.parse_args()
assert a.seconds > 0
a.output.parent.mkdir(parents=True, exist_ok=True)
m = Model(a.trace, a.baseline)
region = m.region(a.region)
group_domains = {}
keys = []
for i, (part, domain, old) in enumerate(zip(m.parts, m.domains, m.baseline)):
    key = ('inside', part.origin if a.whole_parts else i) if part.block in region else ('outside', i)
    keys.append(key)
    if part.block not in region or (a.registers and old < m.register_count and old not in a.registers):
        domain = [old]
    elif a.registers:
        domain = [value for value in domain if value >= m.register_count or value in a.registers]
    group_domains[key] = set(domain) & group_domains.get(key, set(domain))

solver = z3.Optimize()
solver.set(timeout=1000*a.seconds)
groups = {}
for n, (key, domain) in enumerate(group_domains.items()):
    assert domain
    group = {value: z3.BoolVal(True) if len(domain) == 1 else z3.Bool(f'g{n}_v{value}')
             for value in sorted(domain)}
    groups[key] = group
    if len(domain) > 1:
        solver.add(z3.PbEq([(choice, 1) for choice in group.values()], 1))
variables = [groups[key] for key in keys]
rules = set()
for left, right in sorted(m.interference):
    x, y = variables[left], variables[right]
    for reg in x.keys() & y.keys():
        if reg < m.register_count:
            rule = z3.simplify(z3.Or(z3.Not(x[reg]), z3.Not(y[reg])))
            if not z3.is_true(rule):
                rules.add(rule)
solver.add(list(rules))

def location(index):
    return {index: z3.BoolVal(True)} if index < 0 else variables[index]

def same(left, right):
    if left is right:
        return z3.BoolVal(True)
    return z3.Or([z3.And(left[value], right[value]) for value in left.keys() & right.keys()])

def memory(location):
    return z3.Or([choice for value, choice in location.items() if value >= m.register_count])

grouped = defaultdict(list)
terms = []
for left, right, weight, kind, site in m.transfers:
    x, y = location(left), location(right)
    previous = grouped[kind, site]
    moved = z3.simplify(z3.And(z3.Not(same(x, y)),
        *[z3.Not(z3.And(same(x, px), same(y, py))) for px, py in previous]))
    previous.append((x, y))
    terms.extend([(moved, weight), (z3.simplify(z3.And(moved, z3.Or(memory(x), memory(y)))), 2*weight)])
before = m.score(m.baseline)
constant_cost = sum(weight for term, weight in terms if z3.is_true(term))
terms = [(term, weight) for term, weight in terms if not z3.is_true(term) and not z3.is_false(term)]
# Equal Boolean cost predicates share one weight, reducing MaxSAT's objective.
combined = defaultdict(int)
for term, weight in terms:
    combined[term] += weight
terms = list(combined.items())
solver.add(z3.PbLe(terms, before['weighted']-constant_cost-1) if terms else
           z3.BoolVal(constant_cost < before['weighted']))
objective = None
for term, weight in terms:
    objective = solver.add_soft(z3.Not(term), str(weight))
initial = dict(region=a.region, blocks=sorted(region), registers=a.registers,
               whole_parts=a.whole_parts, baseline=before, solver=z3.get_version_string(),
               variables=sum(len(domain)>1 for domain in group_domains.values()),
               constraints=len(rules), terms=len(terms), constant_cost=constant_cost)
print(json.dumps(initial), flush=True)
started = time.monotonic()
status = solver.check()
result = dict(initial, status=str(status), elapsed_seconds=time.monotonic()-started)
if status == z3.unknown:
    result['reason_unknown'] = solver.reason_unknown()
if status != z3.unsat:
    try:
        solution = solver.model()
        assignment = []
        for group in variables:
            chosen = [value for value, choice in group.items() if z3.is_true(solution.eval(choice, model_completion=True))]
            assert len(chosen) == 1, 'not exactly one physical location'
            assignment.append(chosen[0])
        m.verify(assignment)
        after = m.score(assignment)
        symbolic_cost = constant_cost+sum(weight for term, weight in terms if z3.is_true(solution.eval(term)))
        assert symbolic_cost == after['weighted'], 'symbolic and independent costs disagree'
        assert after['weighted'] < before['weighted'], 'no improving feasible assignment'
    except (z3.Z3Exception, AssertionError) as error:
        result['no_validated_solution'] = str(error)
    else:
        result.update(candidate=after, assignment=assignment,
                      changed=sum(x != y for x, y in zip(assignment, m.baseline)))
        if objective is not None:
            result.update(lower_bound=str(objective.lower()+constant_cost),
                          upper_bound=str(objective.upper()+constant_cost))
        m.emit_check(assignment, a.output.with_suffix('.coil'))
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k != 'assignment'}), flush=True)
