#include <stdint.h>
#include <stdio.h>
extern uint64_t stogir_global_load(uint64_t *, uint64_t);
extern uint64_t stogir_global_guard(uint64_t *, uint64_t);
extern uint64_t stogir_global_write(uint64_t *, uint64_t);
int main(void) {
    const uint64_t values[] = {0,1,17,INT64_MAX,UINT64_C(1)<<63,UINT64_MAX};
    if (stogir_global_guard(0,0)!=0) return 1;
    for (unsigned j=0; j<sizeof(values)/sizeof(values[0]); ++j)
        for (uint64_t n=0; n<20; ++n) {
            uint64_t original=values[j], x=original;
            if (stogir_global_load(&x,n)!=(n+1)*original || x!=original) return 2;
            if (stogir_global_guard(&x,n)!=2*n*original || x!=original) return 3;
            uint64_t expected=original, updated=original;
            for (uint64_t i=0; i<n; ++i) { expected+=updated; if (i!=1) ++updated; }
            if (stogir_global_write(&x,n)!=expected || x!=updated) return 4;
        }
    puts("global load forwarding linked AOT: ok");
    return 0;
}
