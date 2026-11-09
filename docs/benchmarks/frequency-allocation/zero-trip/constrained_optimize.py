"""Diagnostic fixed-region optimum for the captured rotated graph.
Requires the build/zero-trip and build/native-recolor-v2 replay inputs.
Not compiler allocation policy. See README.md.
"""
import sys,json,time
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'docs/benchmarks/frequency-allocation')
from model import Model,parse_parts
from recolor import Recolor
import z3
m=Model('build/zero-trip/rotated.trace','build/zero-trip/rotated-replay.log')
new=parse_parts('build/native-recolor-v2/graph-rotated.log','recolor')
initial=[new[p.origin].register if new[p.origin].register>=0 else m.register_count+p.parent for p in m.parts]
m.verify(initial)
region={m.byref[x] for x in (321,664,678,636)}
r=Recolor(m,region,initial)
s=z3.Optimize();s.set(timeout=30000)
xs=[]
for i,d in enumerate(r.domains):
 x=z3.IntVal(next(iter(d))) if len(d)==1 else z3.Int(f'g{i}');xs.append(x)
 if len(d)>1:s.add(z3.Or([x==v for v in sorted(d)]))
for i,neighbors in enumerate(r.neighbors):
 for j in neighbors:
  if j>i and (len(r.domains[i])>1 or len(r.domains[j])>1):s.add(z3.Or(xs[i]>=m.register_count,xs[j]>=m.register_count,xs[i]!=xs[j]))
# Preserve AArch64 phase legality, matching the native recolorer. This graph
# has no selected multi-output definition at these changed internal cuts.
for a,b,w,kind,site in m.transfers:
 if kind!='internal' or site%2!=1 or a<0:continue
 ref,op,*_=m.nodes[site-1]
 if op in (79,80) or (op not in (36,68) and m.canonical(ref)==m.parts[b].parent):continue
 x,y=xs[r.groupof[a]],xs[r.groupof[b]]
 s.add(z3.Or(x==y,z3.And(x<m.register_count,y>=m.register_count)))
edge=m.edges.index((636,628));links=[(a,b) for a,b,w,k,site in m.transfers if k=='edge' and site==edge and a>=0]
for a,b in links:s.add(xs[r.groupof[a]]==xs[r.groupof[b]])
from collections import defaultdict
sites=defaultdict(list);terms=[]
def value(i):return z3.IntVal(i) if i<0 else xs[r.groupof[i]]
for a,b,w,k,site in m.transfers:
 x,y=value(a),value(b);previous=sites[k,site]
 moved=z3.simplify(z3.And(x!=y,*[z3.Or(x!=px,y!=py) for px,py in previous]));previous.append((x,y))
 term=z3.simplify(z3.If(moved,w*z3.If(z3.Or(x>=m.register_count,y>=m.register_count),3,1),0));terms.append(term)
objective=s.minimize(z3.Sum(terms))
s.minimize(z3.Sum([z3.If(x!=v,1,0) for x,v in zip(xs,r.current)]))
print('variables',sum(len(d)>1 for d in r.domains),'groups',len(xs),'initial',m.score(initial),flush=True)
t=time.monotonic();status=s.check();print(status,time.monotonic()-t,flush=True)
if status==z3.sat:
 sol=s.model();colors=[sol.eval(x).as_long() for x in xs];a=[colors[g] for g in r.groupof];m.verify(a);assert all(a[x]==a[y] for x,y in links)
 result=dict(status=str(status),region=sorted(region),assignment=a,score=m.score(a),changes=[dict(parent=m.parts[r.members[g][0]].parent,origin=m.parts[r.members[g][0]].origin,old=r.current[g],new=v) for g,v in enumerate(colors) if v!=r.current[g]])
 Path('build/zero-trip/rotated-opt.json').write_text(json.dumps(result,indent=2)+'\n');m.emit_check(a,Path('build/zero-trip/rotated-opt.coil'));print('bounds',objective.lower(),objective.upper(),flush=True);print('score',m.score(a),'changes',result['changes'],flush=True)
