from pathlib import Path
import subprocess,os,statistics,json,hashlib
r=Path.cwd();d=r/'build/verified-reference-speed';d.mkdir(parents=True,exist_ok=True)
old=Path('/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/allocator-choice-fusion');od=old/'build/verified-reference-speed';od.mkdir(parents=True,exist_ok=True)
c=Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-allocator-choice-fusion/build/bin/coil-candidate')
caller=Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-call-result-projections/build/bin/coil-candidate')
e={k:v for k,v in os.environ.items() if not k.startswith('COIL_')};e.update(COIL_LIBRARY_STATE='0',COIL_TPDE_SERIAL='1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,cwd=r):
 p=subprocess.run(list(map(str,args)),cwd=cwd,env=e,capture_output=True,text=True)
 if p.returncode:(d/'failure.txt').write_text(p.stdout+p.stderr);p.check_returncode()
 return p
kernel=(r/'benchmarks/compiler-gaps/verify-graph.coil').read_text()
for p in [d/'kernel.coil',od/'kernel.coil']:p.write_text(kernel)
(d/'runner.coil').write_text((r/'benchmarks/compiler-gaps/verify-graph-runner.coil').read_text().replace('(for [i 0 128]','(for [i 0 4096]').replace('(* expected 128)','(* expected 4096)'))
frozen={str(root):sha(root/'src/stogir/verify.coil') for root in [old,r]}
rows=[]
for name,root,backend in [('before',old,'stogir'),('after',r,'stogir'),('llvm-before',old,'llvm'),('llvm-after',r,'llvm')]:
 entry=(od if root==old else d)/'kernel.coil'
 p=run([c,'emit-obj',entry,'--backend',backend,'-O3','--no-debug','-o',d/(name+'.o')],root)
 (d/(name+'-build.txt')).write_text(p.stdout+p.stderr)
 rows.append(dict(name=name,cpu=[],object_sha256=sha(d/(name+'.o')),object_bytes=(d/(name+'.o')).stat().st_size))
run([caller,'emit-obj',d/'runner.coil','--backend','llvm','-O3','--no-debug','-o',d/'runner.o'])
for row in rows:run(['cc',d/'runner.o',d/(row['name']+'.o'),'-lm','-o',d/row['name']])
for turn in range(9):
 for row in rows[turn%4:]+rows[:turn%4]:
  p=subprocess.Popen([str(d/row['name'])],env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  _,status,u=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status);out,err=p.communicate();assert p.returncode==0,(row['name'],out,err)
  if 'answers' in row:assert row['answers']==(out+err).decode()
  row['answers']=(out+err).decode()
  if turn:row['cpu'].append(u.ru_utime+u.ru_stime)
for row in rows:row['median_cpu']=statistics.median(row['cpu']);print(row['name'],row['median_cpu'],flush=True)
assert frozen=={str(root):sha(root/'src/stogir/verify.coil') for root in [old,r]}
(d/'results.json').write_text(json.dumps(dict(qualification='Fixed 71856236 emitter; base532a9cd versus private structure-proven integer data references. Unchanged4096-call verifier workload, common b27 LLVM caller, eight rotating CPU samples afterwarmup. No builds/tests/profile overlap timing; source experiment, not whole-bootstrap acceptance',rows=rows,source_hashes=frozen,emitter_sha256=sha(c),caller_sha256=sha(caller),caller_object_sha256=sha(d/'runner.o'),kernel_sha256=sha(d/'kernel.coil'),runner_sha256=sha(d/'runner.coil')),indent=2)+'\n')
