#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
extern void bulk_stream_kernel(void *, const void *, uint64_t);
static uint64_t now(void) { struct timespec t; if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t)) abort(); return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec; }
int main(int argc,char **argv) {
 if(argc!=3) return 2;
 size_t alignment=strtoul(argv[1],0,10), iterations=strtoul(argv[2],0,10);
 if(alignment>15 || !iterations) return 3;
 unsigned char *source=malloc(512),*destination=malloc(512);
 if(!source||!destination) return 4;
 for(size_t i=0;i<512;i++){source[i]=(i*37+19)%251;destination[i]=0xa5;}
 bulk_stream_kernel(destination+32+alignment,source+32+alignment,416);
 for(size_t i=0;i<512;i++) {
   unsigned char expected=i>=32+alignment&&i<32+alignment+416 ? source[i] : 0xa5;
   if(destination[i]!=expected || source[i]!=(i*37+19)%251) return 5;
 }
 uint64_t start=now();
 for(size_t i=0;i<iterations;i++) bulk_stream_kernel(destination+32+alignment,source+32+alignment,416);
 uint64_t elapsed=now()-start,checksum=0;
 for(size_t i=0;i<512;i++) {
   unsigned char expected=i>=32+alignment&&i<32+alignment+416 ? source[i] : 0xa5;
   if(destination[i]!=expected || source[i]!=(i*37+19)%251) return 6;
   checksum+=destination[i];
 }
 printf("{\"cpu_ns\":%llu,\"checksum\":%llu}\n",(unsigned long long)elapsed,(unsigned long long)checksum);
 free(source);free(destination);return 0;
}
