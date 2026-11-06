#include <stdint.h>
#include <stdio.h>

extern uint64_t private_leaf_entry(uint64_t);

int main(void) {
    uint64_t state = UINT64_C(0x9e3779b97f4a7c15);
    for (unsigned i = 0; i < 10000; ++i) {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        uint64_t actual = private_leaf_entry(state);
        if (actual != state + UINT64_C(0x124)) {
            fprintf(stderr, "private AOT leaf answer mismatch at %u\n", i);
            return 1;
        }
    }
    puts("private AOT leaf: 10000 answers pass");
    return 0;
}
