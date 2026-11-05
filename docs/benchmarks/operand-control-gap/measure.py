from pathlib import Path
import subprocess,os,json,resource,statistics,hashlib
r=Path.cwd();d=r/'build/operand-control';c='/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-static-entry-allocations/build/bin/coil-candidate'
env={k:v for k,v in os.environ.items() if not k.startswith('COIL_')};env.update(COIL_LIBRARY_STATE='0',COIL_TPDE_SERIAL='1',COIL_CODEGEN_TIMINGS='1')
def run(a):
 p=subprocess.run(list(map(str,a)),env=env,capture_output=True,text=True);assert p.returncode==0,(a,p.stdout,p.stderr);return p
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run([c,'emit-obj','benchmarks/compiler-gaps/operand-control-runner.coil','--backend','llvm','-O3','--no-debug','-o',d/'runner.o'])
rows=[dict(backend=b,generation_s=[],cpu_s=[]) for b in ['stogir','llvm']]
for turn in range(9):
 for row in rows if turn%2==0 else rows[::-1]:
  b=row['backend'];obj=d/(b+'.o');p=run([c,'emit-obj','benchmarks/compiler-gaps/operand-control.coil','--backend',b,'-O3','--no-debug','-o',obj]);(d/(b+'-'+str(turn)+'.log')).write_text(p.stdout+p.stderr)
  ns=[int(l.split('\t')[3]) for l in p.stderr.splitlines() if l.startswith('coil-codegen\t') and l.split('\t')[2]=='ir-codegen'];assert ns
  if turn:row['generation_s'].append(sum(ns)/1e9)
  h=sha(obj)
  if 'object_sha256' in row:assert h==row['object_sha256']
  row.update(object_sha256=h,object_bytes=obj.stat().st_size)
for row in rows:
 b=row['backend'];run(['cc',d/'runner.o',d/(b+'.o'),'-o',d/b]);run([d/b]);(d/(b+'.asm')).write_text(run(['llvm-objdump','-dr','--no-show-raw-insn',d/(b+'.o')]).stdout)
for turn in range(13):
 for row in rows if turn%2==0 else rows[::-1]:
  before=resource.getrusage(resource.RUSAGE_CHILDREN);run([d/row['backend']]);after=resource.getrusage(resource.RUSAGE_CHILDREN)
  if turn:row['cpu_s'].append(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
for row in rows:row.update(generation_median_s=statistics.median(row['generation_s']),cpu_median_s=statistics.median(row['cpu_s']));print(row,flush=True)
(d/'results.json').write_text(json.dumps(dict(rows=rows,compiler_sha256=sha(Path(c)),runner_sha256=sha(d/'runner.o'),fixture_sha256=sha(r/'benchmarks/compiler-gaps/operand-control.coil'),runner_source_sha256=sha(r/'benchmarks/compiler-gaps/operand-control-runner.coil')),indent=2))
