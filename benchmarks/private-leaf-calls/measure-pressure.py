from pathlib import Path
import hashlib
import json
import os
import statistics
import subprocess
import time

root = Path.cwd()
out = root / 'build/private-pressure-comparison'
out.mkdir(exist_ok=True)
source = root / 'benchmarks/private-leaf-calls/pressure-caller.c'
subprocess.run(['cc', '-O3', '-c', source, '-o', out / 'caller.o'], check=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
frozen = {str(p): sha(p) for p in (root / 'src/stogir/a64').glob('*.coil')}
rows = []
for extra in ['-none', '9', '12', '15']:
    for mode in ['before', 'after']:
        obj = root / f'build/private-pressure-{mode}{extra}.o'
        exe = out / f'{mode}{extra}'
        subprocess.run(['cc', out / 'caller.o', obj, '-o', exe], check=True)
        checked = subprocess.run([exe], capture_output=True, text=True, check=True)
        rows.append(dict(extra=extra, mode=mode, executable=str(exe),
                         object_sha256=sha(obj), object_bytes=obj.stat().st_size,
                         check=checked.stdout, cpu=[], wall=[]))
answers = None
for turn in range(9):
    for row in rows[turn % len(rows):] + rows[:turn % len(rows)]:
        started = time.perf_counter()
        process = subprocess.Popen([row['executable'], 'bench'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, status, usage = os.wait4(process.pid, 0)
        process.returncode = os.waitstatus_to_exitcode(status)
        stdout, stderr = process.communicate()
        assert process.returncode == 0, (row, stdout, stderr)
        if answers is None:
            answers = stdout
        assert stdout == answers and not stderr
        if turn:
            row['cpu'].append(usage.ru_utime + usage.ru_stime)
            row['wall'].append(time.perf_counter() - started)
for row in rows:
    row['median_cpu'] = statistics.median(row['cpu'])
    row['median_wall'] = statistics.median(row['wall'])
    print(row['extra'], row['mode'], row['median_cpu'], flush=True)
assert frozen == {name: sha(name) for name in frozen}
(out / 'results.json').write_text(json.dumps(dict(
    qualification='Small diagnostic only, not actual compiler or bootstrap acceptance. '
                  'Same frozen graph and callee bytes per before/after pair. '
                  'Shared opaque clang O3 caller; 10000 randomized ABI checks and fifty million dependent calls. '
                  'Eight rotating CPU/wall samples after warmup; no own tests/builds overlap timing.',
    caller_source_sha256=sha(source), caller_object_sha256=sha(out / 'caller.o'),
    sources=frozen, answers=answers.decode(), rows=rows), indent=2) + '\n')
