from pathlib import Path
import subprocess,shutil,json,hashlib
r=Path.cwd();d=r/'build/family-gate-validation';d.mkdir(parents=True,exist_ok=True)
old=Path('/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/diamond-user-notification');od=old/'build/family-gate-validation';od.mkdir(parents=True,exist_ok=True)
c=Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-iterative-phi/build/bin/coil-candidate');caller=Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-call-result-projections/build/bin/coil-candidate')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,cwd=r):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True)
 if p.returncode:(d/'failure.txt').write_text(p.stdout+p.stderr);p.check_returncode()
 return p
shutil.copyfile(r/'benchmarks/integer-operands/kernel.coil',od/'kernel.coil')
rows=[('before',old,od/'kernel.coil','stogir',['-O3','--debug-checks']),('after',r,r/'benchmarks/integer-operands/kernel.coil','stogir',['-O3','--debug-checks']),('after-asan',r,r/'benchmarks/integer-operands/kernel.coil','llvm',['-O1','--debug-checks','--sanitize=address'])]
for name,root,entry,backend,flags in rows:run([c,'emit-obj',entry,'-o',d/(name+'.o'),'--backend',backend,*flags],root)
run([caller,'emit-obj',r/'benchmarks/verifier-family-gate/runner.coil','-o',d/'runner.o','--backend','llvm','-O1','--debug-checks','--sanitize=address'])
for name,*_ in rows:
 run(['/opt/homebrew/Cellar/llvm/23.1.4/bin/clang',d/'runner.o',d/(name+'.o'),'-fsanitize=address','-lm','-o',d/name])
 with (d/(name+'-answers.txt')).open('w') as out,(d/(name+'-stderr.txt')).open('w') as err:subprocess.run([str(d/name)],stdout=out,stderr=err,check=True)
 print(name,'passed',flush=True)
assert len({sha(d/(name+'-answers.txt')) for name,*_ in rows})==1
result=dict(cases=len((d/'before-answers.txt').read_text().splitlines()),answer_sha256=sha(d/'before-answers.txt'),kernel_sha256=sha(r/'benchmarks/integer-operands/kernel.coil'),runner_sha256=sha(r/'benchmarks/verifier-family-gate/runner.coil'),source_before=sha(old/'src/stogir/verify.coil'),source_after=sha(r/'src/stogir/verify.coil'),emitter_sha256=sha(c),caller_sha256=sha(caller))
(d/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
