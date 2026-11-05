from pathlib import Path
import subprocess,os,json,hashlib,statistics
r=Path.cwd();d=r/'build/owned-compaction-verifier'
e=dict(os.environ,COIL_LIBRARY_STATE='0',COIL_TPDE_SERIAL='1',COIL_CODEGEN_TIMINGS='1')
compilers={'before':Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-multiply-retirement/build/bin/coil-candidate'),'candidate':Path('/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-owned-compaction/build/bin/coil-candidate')}
rows={n:[] for n in compilers};samples=[];expected='bc4c18ace8f4f32cc3d637cd8c377ed72b07a512c1b111a1b61fa7efbfa3b171'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={str(p):sha(p) for p in (r/'src/stogir').rglob('*.coil')}
for turn in range(14):
 pair={}
 for n in (['before','candidate'] if turn%2==0 else ['candidate','before']):
  obj=d/('repeat-'+n+'.o');p=subprocess.run([str(compilers[n]),'emit-obj','benchmarks/compiler-gaps/verify-graph.coil','--backend','stogir','-O3','--no-debug','-o',str(obj)],cwd=r,env=e,capture_output=True,text=True,check=True)
  records=[x.split('\t') for x in p.stderr.splitlines() if x.startswith('coil-codegen\t')];assert records and all(x[1]=='stogir' and x[2]=='ir-codegen' for x in records)
  assert sha(obj)==expected
  value=sum(int(x[3]) for x in records)/1e9;pair[n]=value
  if turn>=2:rows[n].append(value)
 if turn>=2:samples.append(pair)
assert sources=={str(p):sha(p) for p in (r/'src/stogir').rglob('*.coil')}
result=dict(qualification='12 alternating-order paired IR-codegen samples after two excluded warmups per compiler, same frozen actual verifier source, serial/O3/no-debug/cache off. All28 objects byte-identical. Generation-only repeat; no runtime claim.',compilers={n:dict(path=str(c),sha256=sha(c)) for n,c in compilers.items()},sources=sources,samples=samples,median_s={n:statistics.median(a) for n,a in rows.items()},median_paired_ratio=statistics.median(x['candidate']/x['before'] for x in samples),identical_object_sha256=expected)
(d/'generation-repeat.json').write_text(json.dumps(result,indent=2)+'\n');print(result['median_s'],result['median_paired_ratio'],flush=True)
