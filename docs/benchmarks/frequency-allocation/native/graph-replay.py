from pathlib import Path
import gzip
src=Path('docs/benchmarks/regional-allocation/primitive.trace.gz')
data=gzip.decompress(src.read_bytes()).decode()
rows=[s.split()[1:] for s in data.splitlines() if s.startswith('stogir-snapshot ')]
assert sum(r[0]=='begin' for r in rows)==1
out=['(module native.graph.replay)']
for mod,alias in [('a64.private-leaf','private'),('graph','g'),('node','n'),('strings','strings'),('a64.compile','compile'),('options','options'),('image','image'),('aot.macho','macho')]:
 out.append(f'(import "stogir.{mod}" :as {alias})')
out+=['(import "coil.fs" :as fs)','(import "coil.arraylist" :use [ArrayList])','(import "coil.alloc" :use [malloc-allocator])','(import "coil.result" :use [Ok Err Some None])']
out+=['(defn main [] (-> i32)',' (let [a (malloc-allocator) (mut graph) (g/create a) (mut roots) (ArrayList::new [i32] a)]','  (clear! (mut (.instructions graph))) (clear! (mut (.arities graph)))']
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
out+=['  (match (g/rebuild-constant-index! (mut graph) 8) (Ok [_] 0) (Err [e] (panic "{}" e)))',f'  (set! (.function-prototype graph) {proto})']
out += ['''  (for enabled [false true]
    (let [context (private/with-recolor (private/with-allocation-trace
                    (private/with-induction (private/with-predict (private/with-loop-reloads
                      (private/with-loop-evict (private/no-context) true) true) true) true) true) enabled)]
      (println "graph-native recolor {}" enabled)
      (match (compile/image-with-private graph 1 (slice roots) "_primitive" (options/Options :level 3) a context)
        (Err [message] (panic "{}" message))
        (Ok [owned]
          (let [(mut code) owned]
            (match (macho/image-object code a)
              (Err [message] (panic "{}" message))
              (Ok [bytes]
                (let [(mut bytes) bytes]
                  (match (fs/write-file a (if enabled "build/native-recolor-v2/graph-recolor.o"
                                                   "build/native-recolor-v2/graph-baseline.o") (slice bytes))
                    (Err [_] (panic "write")) (Ok [_] 0))
                  (free! (mut bytes)))))
            (image/release! (mut code)))))))
  (free! (mut roots)) (g/release! (mut graph)) 0))''']
Path('build/native-recolor-v2').mkdir(parents=True, exist_ok=True)
Path('build/native-recolor-v2/graph-replay.coil').write_text('\n'.join(out)+'\n')
print('graph snapshot rows',len(rows))
