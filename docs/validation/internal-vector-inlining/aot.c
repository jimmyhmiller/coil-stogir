#include <stdint.h>
#include <stdio.h>
extern uint64_t internal_vector_caller(void *, const void *);
int main(void) {
 unsigned char source[80],destination[80];
 for(unsigned alignment=0;alignment<16;alignment++) {
  for(unsigned i=0;i<80;i++){source[i]=(i*37+19)%251;destination[i]=0xa5;}
  if(internal_vector_caller(destination+16+alignment,source+16+alignment)!=37) return 1;
  for(unsigned i=0;i<80;i++) {
   unsigned char original=(i*37+19)%251,expected=0xa5;
   if(i>=16+alignment && i<32+alignment) expected=original^(unsigned char)(128+(i-16-alignment)*7);
   if(source[i]!=original || destination[i]!=expected) return 2;
  }
 }
 puts("inlined vector LONG_CONST AOT bytes/guards: pass");return 0;
}
