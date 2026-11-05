from pathlib import Path
import subprocess,os,time,json,statistics,hashlib,re
r=Path.cwd();d=r/'build/hot-code-audit';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for name in ['before','candidate','llvm']:
 obj=d/(name+'-verify.o');asm=subprocess.check_output(['llvm-objdump','-dr','--no-show-raw-insn',str(obj)],text=True);(d/(name+'-verify.asm')).write_text(asm)
 rows.append(dict(name=name,cpu_s=[],object_bytes=obj.stat().st_size,object_sha256=sha(obj)))
assert rows[0]['object_sha256']!=rows[1]['object_sha256']
for turn in range(17):
 for row in rows[turn%3:]+rows[:turn%3]:
  p=subprocess.Popen([str(d/('verify-'+row['name']))],stdout=subprocess.PIPE,stderr=subprocess.PIPE);_,status,u=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status);out,err=p.communicate();assert p.returncode==0,(row['name'],p.returncode,out,err)
  if turn:row['cpu_s'].append(u.ru_utime+u.ru_stime)
for row in rows:row['median_s']=statistics.median(row['cpu_s']);print(row['name'],row['median_s'],row['object_bytes'],flush=True)
(d/'verifier-results.json').write_text(json.dumps(dict(qualification='Actual verifier source unchanged, baseline88e09ce2 vs candidate4055b1b1 backend. Same LLVM O3 caller object constructs opaque2048-node graph, checks layout/reference/type rejections and128 valid results.16 rotating child-CPU samples after excluded warmup. Not bootstrap acceptance.',runner_sha256=sha(d/'verify-runner.o'),fixture_sha256=sha(r/'benchmarks/compiler-gaps/verify-graph.coil'),rows=rows),indent=2))
