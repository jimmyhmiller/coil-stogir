#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
struct Record {uint32_t header; int32_t left,right; uint32_t tag; uint64_t payload,unused;};
_Static_assert(sizeof(struct Record)==32,"record ABI");
extern uint64_t gap_wide_record_scan(void*,int64_t,uint64_t);
static uint64_t reference(const struct Record *p,int64_t n,uint64_t s) {
 for(int64_t i=0;i<n;++i) {
  uint64_t v=(uint64_t)(int64_t)p[i].left+(uint64_t)(int64_t)p[i].right+p[i].payload;
  s=(s*UINT64_C(33)+v)^(s/UINT64_C(128));
 }
 return s;
}
static int64_t cpu_ns(void) {struct timespec t;if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t))abort();return t.tv_sec*INT64_C(1000000000)+t.tv_nsec;}
int64_t benchmark_wide(void *rows,const struct Record *data,int64_t n,int64_t rounds,uint64_t seed) {
 for(int64_t k=-1;k<=n;k=k<2?k+1:(k<n?n:n+1))
  if(gap_wide_record_scan(rows,k,seed)!=reference(data,k,seed))return 1;
 uint64_t actual=seed;int64_t before=cpu_ns();
 for(int64_t j=0;j<rounds;++j)actual=gap_wide_record_scan(rows,n,actual);
 int64_t elapsed=cpu_ns()-before;uint64_t expected=seed;
 for(int64_t j=0;j<rounds;++j)expected=reference(data,n,expected);
 if(actual!=expected)return 2;
 printf("%lld\n",(long long)elapsed);return 0;
}
