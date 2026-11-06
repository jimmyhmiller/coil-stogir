"""Compare Coil decisions with exact pinned ir_fold.h literal rule bodies."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

upstream = Path('/Users/jimmyhmiller/Documents/Code/open-source/ir')
pin = '92171d0a4a36b0acf707f2dea7998de615dd4acd'
assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == pin
source = (upstream / 'ir_fold.h').read_text()
start = source.index('IR_FOLD(AND(_, C_BOOL))')
end = source.index('IR_FOLD(SHL(_, C_U8))', start)
fragment = source[start:end]
types = dict(BOOL=1, U8=2, U16=3, U32=4, U64=5, CHAR=7, I8=8, I16=9, I32=10, I64=11)
ops = dict(OR=46, AND=47, XOR=48)
functions, dispatch = [], []
for number, match in enumerate(re.finditer(r'((?:IR_FOLD\([^\n]+\)\n)+)\{(.*?)^\}', fragment, re.S | re.M)):
    labels = re.findall(r'IR_FOLD\((\w+)\(_, C_(\w+)\)\)', match[1])
    assert labels
    functions.append(f'static Result rule{number}(int op1, int op2, Insn *op2_insn, int opt) {{\n{match[2]}\n}}')
    for op, ty in labels:
        dispatch.append(f'if (opcode=={ops[op]} && ty=={types[ty]}) return rule{number}(11,-2,&literal,(ty<<8)|opcode);')
assert len(dispatch) == 30
code = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <inttypes.h>
typedef struct { union { bool b; int8_t i8; int16_t i16; int32_t i32; int64_t i64; uint64_t u64; } val; } Insn;
typedef struct { int kind, source, opcode; } Result;
#define IR_NOT 45
#define IR_UNUSED 0
#define IR_OPT_TYPE_MASK 0xff00
#define IR_FOLD_COPY(ref) return (Result){2,ref,0}
#define IR_FOLD_NEXT return (Result){3,0,0}
#define IR_FOLD_RESTART return (Result){4,op1,opt & 255}
''' + '\n'.join(functions) + '''
static Result decide(int opcode,int ty,uint64_t bits) {
Insn literal; literal.val.u64=bits;
''' + '\n'.join(dispatch) + r'''
return (Result){-1,0,0};
}
int main(void) {
int types[]={1,2,3,4,5,7,8,9,10,11};
for(int t=0;t<10;t++) {
 int ty=types[t], width=ty==1?1:((ty==2||ty==7||ty==8)?8:(ty==3||ty==9)?16:(ty==4||ty==10)?32:64);
 uint64_t mask=width==64?UINT64_MAX:(((uint64_t)1<<width)-1);
 uint64_t literals[]={0,mask,mask & 0xa5};
 for(int op=46;op<=48;op++) for(int i=0;i<3;i++) for(int reverse=0;reverse<2;reverse++) {
  Result r=decide(op,ty,literals[i]);
  printf("BIT %d %d %" PRIu64 " %s %d %d %d\n",ty,op,literals[i],reverse?"true":"false",r.kind,r.source,r.opcode);
 }
}
return 0;
}
'''
out = Path('build/bit-literal-oracle')
out.mkdir(parents=True, exist_ok=True)
c = out / 'oracle.c'
c.write_text(code)
subprocess.run(['cc', '-O1', '-fsanitize=address', c, '-o', out/'oracle'], check=True)
answer = subprocess.check_output([str(out/'oracle')], text=True)
(out/'expected.txt').write_text(answer)
actual_file = Path(sys.argv[1])
actual = [line for line in actual_file.read_text().splitlines() if line.startswith('BIT ')]
expected = answer.splitlines()
assert len(actual) == len(expected) == 180
assert actual == expected, next(((a,b) for a,b in zip(actual,expected) if a!=b), None)
report = dict(upstream=pin, fragment_sha256=hashlib.sha256(fragment.encode()).hexdigest(),
              c_sha256=hashlib.sha256(code.encode()).hexdigest(), actual_file=str(actual_file),
              exact_decisions=len(actual), asan='PASS', note='Commutative left-literal cases normalized to the original right-literal rules; input11, literal-2.')
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
