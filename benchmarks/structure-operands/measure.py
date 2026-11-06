from pathlib import Path
import subprocess,os,statistics,json,hashlib
r=Path.cwd();b=r/'build/structure-speed';old=Path('/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/finite-countdown')
env={k:v for k,v in os.environ.items() if not k.startswith('COIL_')};env.update(COIL_LIBRARY_STATE='0',COIL_TPDE_SERIAL='1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
objects={'before':old/'build/structure-speed/before.o','after':b/'after.o','llvm-before':old/'build/structure-speed/llvm-before.o','llvm-after':b/'llvm-after.o'}
for name,obj in objects.items():subprocess.run(['cc',str(b/'runner.o'),str(obj),'-lm','-o',str(b/name)],check=True)
rows={name:[] for name in objects};answers={}
for turn in range(9):
 names=list(objects);names=names[turn%4:]+names[:turn%4]
 for name in names:
  p=subprocess.Popen([str(b/name)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  _,status,u=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status);out,err=p.communicate();assert p.returncode==0,(name,out,err)
  answers[name]=(out+err).decode()
  if turn:rows[name].append(u.ru_utime+u.ru_stime)
result=dict(qualification='Fixed b27ffeb4 emitter, unchanged arithmetic verifier kernel and4096-call opaque LLVM caller with malformed type/reference/arity checks; four variants,eight rotating CPU samples after warmup. No builds/tests/sampling overlap. Source change only, no integrated candidate/whole-bootstrap claim.',cpu=rows,median_cpu={n:statistics.median(v) for n,v in rows.items()},objects={n:sha(o) for n,o in objects.items()},caller=sha(b/'runner.o'),verify_source=sha(r/'src/stogir/verify.coil'),before_verify_source=sha(old/'src/stogir/verify.coil'),answers=answers)
(b/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result['median_cpu'])
