"""Replay instruction bytes from the audited compiler object; never certify bindings."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

obj = Path(sys.argv[1])
assert hashlib.sha256(obj.read_bytes()).hexdigest() == '0aed11120770a106a1ba7e15fdefcfa1fcd3d1a8cf01946b18a101ff713e3efe'
names = ['_stogir.graph.borrow-node', '_stogir.graph.operand', '_stogir.graph.lookup']
output = subprocess.check_output([
    '/opt/homebrew/opt/llvm/bin/llvm-objdump', '-d',
    '--disassemble-symbols=' + ','.join(names), str(obj)], text=True)
bodies = {}
current = None
for line in output.splitlines():
    label = re.fullmatch(r'[0-9a-f]+ <([^>]+)>:', line)
    if label:
        current = label[1]
        bodies[current] = []
    elif current:
        instruction = re.match(r'\s*[0-9a-f]+:\s+([0-9a-f]{8})\s', line)
        if instruction:
            bodies[current].append(int(instruction[1], 16))
assert set(bodies) == set(names)
assert [len(bodies[name]) for name in names] == [62, 53, 77]
assert bodies[names[2]][-1] == 0  # Adjacent object padding is not decoded as code.
prefix = '''(module stogir.tests.actual-leaf-effects)
(import "stogir.a64.leaf-effects" :as effects)
(import "stogir.bytes" :as bytes)
(import "coil.arraylist" :use [ArrayList])
(import "coil.alloc" :use [malloc-allocator])
(import "coil.result" :use [Some None])
(defn main [] (-> i32)
 (let [(mut text) (ArrayList::new [u8] (malloc-allocator))]
'''
source = [prefix]
expected = [0x1007F, 0x1001F, None]
for name, mask in zip(names, expected):
    source.append('  (clear! (mut text))')
    source.extend(f'  (bytes/append32! (mut text) (: {word} u32))' for word in bodies[name])
    if mask is None:
        source.append('  (match (effects/text (slice text)) (None [] 0) (Some [_] (panic "padding accepted")))')
        # This is an explicit fixture boundary, not a production trimming rule.
        source.append('  (set! (.len text) (- (len text) 4))')
        mask = 0x3007F
    source.append(f'  (match (effects/text (slice text)) (None [] (panic "{name} declined"))'
                  f' (Some [mask] (assert (= mask (: {mask} u64)))))')
source.append('  (free! (mut text)))\n (println "three actual compiler leaf write sets and padding rejection pass")\n 0)\n')
out = Path('build/leaf-effects')
(out / 'actual-bodies.json').write_text(json.dumps(bodies, indent=2) + '\n')
(out / 'actual-validation.coil').write_text('\n'.join(source))
