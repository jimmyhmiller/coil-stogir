#!/usr/bin/env python3
"""Create an isolated diagnostic compiler; never edits the source checkout.

The instrumentation is intentionally absent from the production compiler. Run
the generated compiler with COIL_STOGIR_BBCOUNT=1 and the counter runtime loaded.
Counters use the emitter's reserved x16/x17 and do not change NZCV. Their cost
makes the resulting host unsuitable for runtime timing comparisons.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
source, output = a.source.resolve(), a.output.resolve()
output.mkdir(parents=True, exist_ok=False)
shutil.copytree(source / 'src', output / 'src')
for name in ('stage0.py', 'toolchain_stamp.py'):
    dest = output / 'scripts/compiler' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'scripts/compiler' / name, dest)
(output / 'build/bin').mkdir(parents=True)
(output / 'build/bin/native').symlink_to(source / 'build/bin/native', target_is_directory=True)

def replace(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old, text.count(old))
    path.write_text(text.replace(old, new))

vendor = output / 'src/compiler/stogir/stogir'
counter = Path(__file__).with_name('block-count.coil')
shutil.copy2(counter, vendor / 'a64/block-count.coil')
function = vendor / 'a64/function.coil'
replace(function, '(module stogir.a64.function)',
        '(module stogir.a64.function)\n(import "stogir.a64.block-count" :as block-count)')
line = '          (set! (mut labels) (cast i64 reference) (len (.text output)))'
replace(function, line, line + '\n          (block-count/emit! (mut (.text output)) (cast i32 reference))')
adapter = output / 'src/compiler/backend/codegen_stogir.coil'
replace(adapter, '(module coil.compiler.codegen_stogir)',
        '(module coil.compiler.codegen_stogir)\n(import "stogir.a64.block-count" :as block-count)')
line = '(defn module-create [(a (dyn Allocator)) (trace bool)] (-> Module)'
replace(adapter, line, line + '\n  (when (env-flag c"COIL_STOGIR_BBCOUNT" "COIL_STOGIR_BBCOUNT") (block-count/enable!))')
line = '          (match (native/image-with-private (.graph definition) (.entry definition)'
replace(adapter, line, '          (block-count/set-function! (.name f))\n' + line)
line = '      (match (cond (and (!= (p/cast usize module) 0) (> (.native-certified module) 0) optimized)'
replace(adapter, line, '      (block-count/set-function! (.name f))\n' + line)

changed = ['src/compiler/backend/codegen_stogir.coil',
           'src/compiler/stogir/stogir/a64/function.coil',
           'src/compiler/stogir/stogir/a64/block-count.coil']
meta = dict(source=str(source),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(),
            source_status=subprocess.check_output(['git', 'status', '--porcelain', '--', 'src'], cwd=source, text=True),
            instrumentation={name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in changed},
            qualification='Isolated block-count diagnostic; not a production policy or runtime measurement.')
(output / 'provenance.json').write_text(json.dumps(meta, indent=2) + '\n')
print(output)
