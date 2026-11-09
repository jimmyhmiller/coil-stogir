"""Rebuild one lossless stogir-snapshot and emit the retained research pipeline."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();rows=[s.split()[1:] for s in a.snapshot.read_text().splitlines() if s.startswith('stogir-snapshot ')]
assert sum(r[0]=='begin' for r in rows)==1
out=['(module inspect.shift-mask)']
for mod,alias in [('graph','g'),('node','n'),('strings','strings'),('a64.compile','compile'),('a64.private-leaf','private'),('options','options'),('image','image')]:out.append(f'(import "stogir.{mod}" :as {alias})')
out+=['(import "coil.arraylist" :use [ArrayList])','(import "coil.alloc" :use [malloc-allocator])','(import "coil.result" :use [Ok Err Some None])','(defn main [] (-> i32)',' (let [a (malloc-allocator) (mut graph) (g/create a) (mut roots) (ArrayList::new [i32] a)]','  (clear! (mut (.instructions graph))) (clear! (mut (.arities graph)))']
for r in rows:
 kind=r[0];v=list(map(int,r[1:])) if kind!='end' else []
 if kind=='begin':entry,proto=v
 elif kind=='root':out.append(f'  (push! (mut roots) (: {v[0]} i32))')
 elif kind=='string':
  sid,count,*data=v;assert len(data)==count
  values=' '.join(f'(: {x} u8)' for x in data)
  out.append(f'  (match (strings/intern! (mut (.strings graph)) [{values}]) (Some [id] (assert (= id {sid}))) (None [] (panic "string failure")))')
 elif kind in ('constant','instruction'):
  arity,header,o1,o2,o3=v;field='constants' if kind=='constant' else 'instructions';meta='constant-spans' if kind=='constant' else 'arities'
  out.append(f'  (push! (mut (.{field} graph)) (n/Node :header (: {header} u32) :op1 (: {o1} i32) :op2 (: {o2} i32) :op3 (: {o3} i32)))')
  out.append(f'  (push! (mut (.{meta} graph)) (: {arity} i32))')
out+=['  (match (g/rebuild-constant-index! (mut graph) 8) (Ok [_] 0) (Err [e] (panic "{}" e)))',f'  (set! (.function-prototype graph) {proto})','  (let [(mut context) (private/no-context)]']
for flag in ['loop-evict','loop-reloads','predict','induction','rotate','regional','hoist-loads','strength','allocation-trace']:
 out.append(f'   (set! context (private/with-{flag} context true))')
out += [f'   (match (compile/image-with-private graph {entry} (slice roots) "_captured_views" (options/Options :level 3) a context)', '    (Err [e] (panic "{}" e))','    (Ok [owned] (let [(mut code) owned]','     (print "text") (for byte (.text code) (print " {}" byte)) (println "")','     (println "text-bytes {}" (len (.text code)))','     (image/release! (mut code))))))','  (free! (mut roots)) (g/release! (mut graph)))',' 0)']
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(out)+'\n')
