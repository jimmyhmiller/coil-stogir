#!/usr/bin/env python3
"""Build an isolated library with exact old/new transfer and domain checks."""
import argparse
import gzip
from pathlib import Path
import shutil
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
a=p.parse_args()
root=Path.cwd(); out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
shutil.copytree(root/'src',out/'src');shutil.copy(root/'Coil.toml',out/'Coil.toml')
(out/'tests').mkdir();(out/'build/regional-native').mkdir(parents=True)
for name in ('regional-native','allocation-regional','allocation-recolor','recolor-native'):
 shutil.copy(root/f'tests/{name}.coil',out/f'tests/{name}.coil')
(out/'tests/primitive.coil').write_bytes(gzip.decompress(
 (root/'docs/benchmarks/frequency-allocation/regional-native/primitive.coil.gz').read_bytes()))
for name in ('allocation-transfers','allocation-recolor'):
 old=subprocess.check_output(['git','show',f'579c817:src/stogir/{name}.coil'],text=True)
 old=old.replace(f'(module stogir.{name})',f'(module stogir.{name}-reference)')
 (out/f'src/stogir/{name}-reference.coil').write_text(old)
p=out/'src/stogir/allocation-transfers.coil';s=p.read_text()
s=s.replace('(module stogir.allocation-transfers)', '(module stogir.allocation-transfers)\n(import "stogir.allocation-transfers-reference" :as oracle)')
s=s.replace('(defn build [','(defn build-indexed [')
s+='''
(defn build [(parts (ArrayList a/Part)) (index loc/Index) (graph g/Graph)
              (blocks cfg/Blocks) (scheduled schedule/Schedule) (depths (ArrayList i32)) (matched machine/Plan)
              (allocator (dyn Allocator))] (-> (Result (ArrayList rc/Copy) (slice u8)))
  (match (build-indexed parts index graph blocks scheduled depths matched allocator)
    (Err [message] (panic "indexed transfers: {}" message))
    (Ok [actual]
      (match (oracle/build parts index graph blocks scheduled depths matched allocator)
        (Err [message] (panic "reference transfers: {}" message))
        (Ok [owned]
          (let [(mut expected) owned]
            (assert (= (len actual) (len expected)))
            (for [i 0 (len actual)]
              (let [x (get actual i) y (get expected i)]
                (assert (= (.part (.source x)) (.part (.source y))))
                (assert (loc/same? (.literal (.source x)) (.literal (.source y))))
                (assert (= (.target x) (.target y))) (assert (= (.site x) (.site y)))
                (assert (= (.weight x) (.weight y))) (assert (= (.store-only x) (.store-only y)))))
            (println "exact transfer oracle: {} parts, {} copies" (len parts) (len actual))
            (free! (mut expected)) (Ok actual)))))))
'''
p.write_text(s)
p=out/'src/stogir/allocation-recolor.coil';s=p.read_text()
s=s.replace('(module stogir.allocation-recolor)', '(module stogir.allocation-recolor)\n(import "stogir.allocation-recolor-reference" :as oracle)')
s=s.replace('(defn create-scoped [','(defn create-scoped-indexed [')
s+='''
(defn create-scoped [(parts (ArrayList a/Part)) (allowed u64) (mutable (slice bool)) (allocator (dyn Allocator))] (-> Problem)
  (let [actual (create-scoped-indexed parts allowed mutable allocator)
        (mut expected) (oracle/create-scoped parts allowed mutable allocator)]
    (assert (= (len (.domains actual)) (len (.domains expected))))
    (for [i 0 (len parts)]
      (let [x (get (.domains actual) i) y (get (.domains expected) i) (mut j) 0]
        (assert (= (.registers x) (.registers y))) (assert (= (.spill x) (.spill y)))
        (for neighbor (get (.neighbors expected) i)
          (when (or (= (len mutable) 0) (get mutable i) (get mutable (cast i64 neighbor)))
            (assert (= (get (get (.neighbors actual) i) j) neighbor)) (set! j (+ j 1))))
        (assert (= j (len (get (.neighbors actual) i))))))
    (println "exact domain/interference oracle: {} parts" (len parts))
    (oracle/release! (mut expected)) actual))
'''
p.write_text(s)
print(out)
