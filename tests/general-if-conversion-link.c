#include <stdint.h>
#include <stdio.h>
extern uint64_t stogir_general_select(uint64_t, uint64_t, uint64_t, const uint64_t *);
int main(void) {
    const uint64_t values[] = {0, 1, 17, INT64_MAX, UINT64_C(1)<<63, UINT64_MAX};
    for (unsigned c=0; c<3; ++c)
        for (unsigned i=0; i<sizeof(values)/sizeof(values[0]); ++i)
            for (unsigned j=0; j<sizeof(values)/sizeof(values[0]); ++j) {
                uint64_t x=values[i], y=values[j];
                uint64_t expected=c ? 2*x*y : x+y;
                if (stogir_general_select(c,x,y,0)!=expected) return 1;
            }
    puts("general if-conversion linked AOT: ok");
    return 0;
}
