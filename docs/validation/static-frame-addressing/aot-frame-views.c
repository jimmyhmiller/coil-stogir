#include <stdint.h>
#include <assert.h>
#include <string.h>
static uint64_t copy_frame(uint8_t *out,uint8_t *in,uint64_t offset,uint64_t count,
 uint8_t *padding,uint64_t large,uint64_t mask) {
 for(uint64_t i=0;i<count;i++) { uint8_t b=in[offset+i]; out[i]=b; in[offset+i]=b^(uint8_t)mask; }
 return large && padding[65535]!=0x5a ? 0 : 13;
}
extern uint64_t static_views(uint8_t *,uint64_t (*)(uint8_t *,uint8_t *,uint64_t,uint64_t,uint8_t *,uint64_t,uint64_t));
int main(void) {
 uint8_t output[48]; memset(output,0xa5,sizeof(output));
 assert(static_views(output+1,copy_frame)==13);
 for(unsigned i=0;i<48;i++) {
  uint8_t expected=0xa5;
  if(i>=1 && i<=16) expected=(uint8_t)((i-1)*37+19);
  if(i>=17 && i<=32) expected=(uint8_t)(((i-17)*37+19)^0xa7);
  assert(output[i]==expected);
 }
 return 0;
}
