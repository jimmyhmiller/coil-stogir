from pathlib import Path
import subprocess,os,json
c='/Users/jimmyhmiller/Documents/Code/projects/coil/.worktrees/stogir-static-entry-allocations/build/bin/coil-candidate';env=dict(os.environ,COIL_LIBRARY_STATE='0');rows=[]
for name in ['bulk','jit-bulk-pressure','inline-stack-results','static-stack','jit-mem2ssa','aot-bulk-link']:
 args=[c,'run','tests/'+name+'.coil','--debug-checks','--sanitize=address']
 if name=='aot-bulk-link':
  for suffix in ['copy_dynamic','move_dynamic','zero_dynamic','copy_17','move_63','move_65','zero_9','pressure_forward','pressure_backward']:
   path=Path('/tmp/coil-stogir-bulk-'+suffix.replace('_','-',1)+'.o') if suffix.startswith('pressure') else Path('/tmp/coil-stogir-bulk-'+suffix+'.o')
   # Native fixture naming uses a dash before each operation.
   if not path.exists():
    matches=list(Path('/tmp').glob('*bulk*'+suffix.split('_')[-1]+'*.o'));raise AssertionError((path,matches))
   args+=['--link-flag',str(path)]
 p=subprocess.run(args,env=env,capture_output=True,text=True);Path('build/bulk-streams/'+name+'.log').write_text(p.stdout+p.stderr)
 rows.append(dict(test=name,exit=p.returncode));Path('build/bulk-streams/validation.json').write_text(json.dumps(rows,indent=2));print(name,p.returncode,flush=True);assert p.returncode==0,(name,p.stdout[-3000:],p.stderr[-3000:])
