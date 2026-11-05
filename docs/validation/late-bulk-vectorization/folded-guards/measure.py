from pathlib import Path
import subprocess,hashlib,json,statistics,os
r=Path.cwd();d=r/'build/bulk-streams';old=r.parent/'profile-guided-pipeline/build/bulk-streams';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):
 p=subprocess.run(list(map(str,a)),capture_output=True,text=True);assert p.returncode==0,(a,p.returncode,p.stdout,p.stderr);return p
assert sha(old/'copy416.o')!=sha(d/'copy416.o')

run(['cc','-O3','-c',d/'runner.c','-o',d/'runner.o'])
rows=[]
for name,obj in [('scalar',old/'copy416.o'),('late',d/'copy416.o'),('llvm',d/'llvm-copy416.o')]:
 run(['cc',d/'runner.o',obj,'-o',d/name]);(d/(name+'.asm')).write_text(run(['llvm-objdump','-dr','--no-show-raw-insn',obj]).stdout)
 for alignment in [0,1,7,15]:rows.append(dict(name=name,alignment=alignment,cpu_ns=[],object_sha256=sha(obj),object_bytes=obj.stat().st_size))
for turn in range(9):
 for row in rows[turn%len(rows):]+rows[:turn%len(rows)]:
  p=run([d/row['name'],row['alignment'],1000000]);answer=json.loads(p.stdout)
  if turn:row['cpu_ns'].append(answer['cpu_ns'])
  if 'checksum' in row:assert row['checksum']==answer['checksum']
  row['checksum']=answer['checksum']
for row in rows:
 row['median_cpu_ns']=statistics.median(row['cpu_ns']);print(row['name'],row['alignment'],row['median_cpu_ns']/1e6,flush=True)
(d/'results.json').write_text(json.dumps(dict(qualification='1M opaque 416-byte copies; same C caller object, source unchanged plus complete destination guard/byte oracles before and after timing. LLVM O3 kernel compiled from equivalent Coil aggregate assignment. Eight rotating process-CPU-clock samples after one excluded warmup; no bootstrap acceptance inferred.',source_files={str(p.relative_to(r)):sha(p) for p in sorted((r/'src/stogir').rglob('*.coil'))},source_sha256=sha(r/'src/stogir/bulk.coil'),old_source_sha256=sha(r.parent/'profile-guided-pipeline/src/stogir/bulk.coil'),generator_sha256=sha(r/'benchmarks/compiler-gaps/bulk-streams.coil'),llvm_source_sha256=sha(r/'benchmarks/compiler-gaps/bulk-stream-llvm.coil'),runner_sha256=sha(d/'runner.o'),runner_source_sha256=sha(d/'runner.c'),rows=rows),indent=2))
