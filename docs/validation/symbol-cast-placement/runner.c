#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
extern uint64_t symbol_placement(uint64_t,uint64_t,uint64_t*);
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
int main(void){
 const uint64_t counts[]={0,1,2,15,16,17,32},choices[]={0,1,3,15,31,1000,UINT64_MAX};
 for(unsigned c=0;c<7;c++)for(unsigned s=0;s<7;s++){
  uint64_t out[2]={0x1122334455667788ull,0x8877665544332211ull};int expected=0;
  for(uint64_t i=0;i<counts[c];i++)for(uint64_t j=0;j<16;j++)if(i==choices[s]+j)expected=65+j;
  if(symbol_placement(counts[c],choices[s],out)!=counts[c]||out[1]!=0x8877665544332211ull)return 2;
  if(expected? *(unsigned char*)(uintptr_t)out[0]!=expected : out[0]!=0x1122334455667788ull)return 3;
 }
 if(symbol_placement(0,0,NULL)!=0)return 4;
 uint64_t out[2]={0x1122334455667788ull,0x8877665544332211ull},start=now(),sum=0;
 for(unsigned i=0;i<4;i++)sum+=symbol_placement(1000000,1000000000,out);
 uint64_t elapsed=now()-start;
 if(sum!=4000000||out[0]!=0x1122334455667788ull||out[1]!=0x8877665544332211ull)return 5;
 printf("%llu\n",(unsigned long long)elapsed);return 0;
}
