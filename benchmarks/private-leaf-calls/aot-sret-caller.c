#include <stdint.h>
#include <stdio.h>
extern uint64_t private_sret_entry(uint64_t *, uint64_t);
int main(void) {
    uint64_t state = UINT64_C(0x9e3779b97f4a7c15), cell = 0;
    for (unsigned i = 0; i < 10000; ++i) {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        cell = ~state;
        if (private_sret_entry(&cell, state) != state || cell != state)
            return 1;
    }
    puts("private x8 indirect result: 10000 AOT answers pass");
    return 0;
}
