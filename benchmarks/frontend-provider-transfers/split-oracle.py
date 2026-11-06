"""Run the pinned C split selector independently, using Coil's two-phase units."""
from pathlib import Path
import argparse,subprocess,hashlib,json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--upstream',type=Path,default=Path('/Users/jimmyhmiller/Documents/Code/open-source/ir'))
a=p.parse_args()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.upstream,text=True).strip()=='92171d0a4a36b0acf707f2dea7998de615dd4acd'
source=(a.upstream/'ir_ra.c').read_text()
def extract(name):
    at=source.index('static ',source.index(name)-80)
    # Locate the actual signature, not a preceding helper.
    while name not in source[at:source.index('{',at)]:at=source.index('static ',at+7)
    brace=source.index('{',at);depth=1;end=brace+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[at:end]
functions='\n'.join(extract(n) for n in ['ir_ival_has_hole_between','ir_block_from_live_pos','ir_find_optimal_split_position'])
assert hashlib.sha256(functions.encode()).hexdigest()=='1aae80c9ee6c67620f8dfda14ad64ee3243ddb458754d21681f33d9fb7ea2177'
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
typedef int32_t ir_live_pos;
typedef int32_t ir_ref;
typedef struct ir_live_range {ir_live_pos start,end;struct ir_live_range *next;} ir_live_range;
typedef struct {ir_live_range range;ir_live_pos end;} ir_live_interval;
typedef struct {ir_ref start,end;uint32_t loop_depth,loop_header,idom,flags;} ir_block;
typedef struct {ir_block *cfg_blocks;uint32_t *cfg_map;uint32_t cfg_blocks_count;} ir_ctx;
#define IR_ASSERT assert
#define IR_BB_LOOP_HEADER 1
#define IR_LIVE_POS_TO_REF(p) ((p)/2)
#define IR_LOAD_LIVE_POS_FROM_REF(r) ((r)*2)
#define IR_DEF_LIVE_POS_FROM_REF(r) ((r)*2+1)
'''
main=r'''
int main(void) {
 ir_block blocks[8]={{0},{0,4,0,0,1,0},{5,9,1,0,1,1},{10,14,1,2,2,0},
 {15,19,2,2,3,1},{20,24,2,4,4,0},{25,29,1,2,4,0},{30,34,0,0,2,0}};
 uint32_t mapping[35];for(unsigned i=0;i<35;i++)mapping[i]=i/5+1;
 ir_ctx ctx={blocks,mapping,7};
 for(int shape=0;shape<4;shape++) {
  ir_live_range b={0,0,0},c={0,0,0};ir_live_interval v={{0,70,0},70};
  if(shape==1){v.range.end=20;b=(ir_live_range){25,70,0};v.range.next=&b;}
  if(shape==2){v.range.end=45;b=(ir_live_range){46,70,0};v.range.next=&b;}
  if(shape==3){v.range.end=10;b=(ir_live_range){15,35,&c};c=(ir_live_range){40,70,0};v.range.next=&b;}
  uint64_t hash=UINT64_C(1469598103934665603);int count=0;
  for(int lo=0;lo<70;lo++)for(int hi=lo;hi<70;hi++)for(int pref=0;pref<2;pref++){
   int selected=ir_find_optimal_split_position(&ctx,&v,lo,hi,pref);
   hash=(hash^(uint64_t)selected)*UINT64_C(1099511628211);count++;
  }
  printf("%d %d %" PRIu64 "\n",shape,count,hash);
 }
}
'''
out=Path('build/loop-split-oracle');out.mkdir(parents=True,exist_ok=True)
(out/'oracle.c').write_text(prelude+functions+main)
clang=Path(subprocess.check_output(['llvm-config','--bindir'],text=True).strip())/'clang'
subprocess.run([str(clang),'-O1','-fsanitize=address',str(out/'oracle.c'),'-o',str(out/'oracle')],check=True)
r=subprocess.run([str((out/'oracle').resolve())],capture_output=True,text=True,check=True)
report=dict(upstream='92171d0a4a36b0acf707f2dea7998de615dd4acd',functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),rows=[dict(zip(['shape','count','hash'],map(int,line.split()))) for line in r.stdout.splitlines()])
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
