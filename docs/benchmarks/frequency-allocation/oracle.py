#!/usr/bin/env python3
"""Search coordinated regional assignments with Z3; never used by native codegen.

A timeout is not an optimality proof. All feasible outputs are checked again by
the Python model and exported for the library's independent allocation verifier.
"""
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
p.add_argument('--region', type=int, required=True, help='dominator-tree root block index')
p.add_argument('--seconds', type=int, default=45)
p.add_argument('--bitvectors', action='store_true', help='encode finite physical locations directly as bits')
p.add_argument('--registers', type=int, nargs='+', help='recolor only these register channels and spilled gaps')
p.add_argument('--first-feasible', action='store_true', help='stop at a feasible improvement without claiming optimality')
p.add_argument('--whole-parts', action='store_true', help='keep each existing interval child in one location inside the region')
a = p.parse_args()
if a.seconds <= 0:
    p.error('seconds must be positive')
m = Model(a.trace, a.baseline)
region = m.region(a.region)
a.output.parent.mkdir(parents=True, exist_ok=True)
solver = z3.Solver() if a.first_feasible else z3.Optimize()
solver.set(timeout=1000*a.seconds)
extent = max([m.register_count + max(part.parent for part in m.parts),
              *[-min(left, right, 0) for left, right, *_ in m.transfers]])
bits = extent.bit_length()+1
constant = (lambda value: z3.BitVecVal(value, bits)) if a.bitvectors else z3.IntVal
variable_type = (lambda name: z3.BitVec(name, bits)) if a.bitvectors else z3.Int
variables = []
variable_count = 0
group_domains = {}
domains = []
for i, (part, domain, old) in enumerate(zip(m.parts, m.domains, m.baseline)):
    if a.registers:
        assert all(0 <= reg < m.register_count for reg in a.registers)
        domain = ([old] if old < m.register_count and old not in a.registers else
                  [reg for reg in domain if reg >= m.register_count or reg in a.registers])
    key = part.origin if a.whole_parts else i
    domains.append(domain)
    if part.block in region:
        group_domains[key] = set(domain) & group_domains.get(key, set(domain))
groups = {}
for i, (part, domain, old) in enumerate(zip(m.parts, domains, m.baseline)):
    key = part.origin if a.whole_parts else i
    domain = sorted(group_domains[key]) if part.block in region else [old]
    assert old in domain
    if len(domain) == 1:
        variables.append(constant(old))
    elif key in groups:
        variables.append(groups[key])
    else:
        variable = variable_type(f'location_{i}')
        variables.append(variable)
        groups[key] = variable
        variable_count += 1
        solver.add(z3.Or([variable == value for value in domain]))
        if not a.first_feasible:
            solver.set_initial_value(variable, constant(old))
for left, right in sorted(m.interference):
    x, y = variables[left], variables[right]
    rule = z3.simplify(z3.Or(x >= m.register_count, y >= m.register_count, x != y))
    if not z3.is_true(rule):
        solver.add(rule)

def location(index):
    return constant(index) if index < 0 else variables[index]

grouped = defaultdict(list)
terms = []
for left, right, weight, kind, site in m.transfers:
    x, y = location(left), location(right)
    previous = grouped[kind, site]
    distinct = z3.And(x != y, *[z3.Or(x != px, y != py) for px, py in previous])
    previous.append((x, y))
    term = z3.simplify(z3.If(distinct,
        weight*z3.If(z3.Or(x >= m.register_count, y >= m.register_count), 3, 1), 0))
    terms.append(term)
cost = z3.Sum(terms)
before = m.score(m.baseline)
solver.add(cost < before['weighted'])
objective = None if a.first_feasible else solver.minimize(cost)
print(json.dumps(dict(region=a.region, blocks=len(region), variables=variable_count,
                      baseline=before, solver=z3.get_version_string())), flush=True)
started = time.monotonic()
status = solver.check()
result = dict(status=str(status), elapsed_seconds=time.monotonic()-started,
              region=a.region, blocks=sorted(region), variables=variable_count,
              baseline=before, solver=z3.get_version_string(), seconds_limit=a.seconds)
result['encoding'] = 'bitvectors' if a.bitvectors else 'integers'
result['registers'] = a.registers
result['first_feasible'] = a.first_feasible
result['whole_parts'] = a.whole_parts
if status == z3.unknown:
    result['reason_unknown'] = solver.reason_unknown()
if status != z3.unsat:
    try:
        solution = solver.model()
        assignment = [solution.eval(value, model_completion=True).as_long() for value in variables]
        m.verify(assignment)
        after = m.score(assignment)
        assert after['weighted'] == solution.eval(cost).as_long(), 'symbolic cost disagrees'
        assert after['weighted'] < before['weighted'], 'no improving feasible solution'
    except (z3.Z3Exception, AssertionError) as error:
        result['no_validated_solution'] = str(error)
    else:
        result.update(candidate=after, assignment=assignment,
                      changed=sum(x != y for x, y in zip(assignment, m.baseline)))
        if objective is not None:
            result.update(lower_bound=str(objective.lower()), upper_bound=str(objective.upper()))
        m.emit_check(assignment, a.output.with_suffix('.coil'))
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k != 'assignment'}), flush=True)
