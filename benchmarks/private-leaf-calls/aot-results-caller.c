#include <stdint.h>
#include <stdio.h>
extern uint64_t private_sret_entry(uint64_t *, uint64_t);
extern uint64_t private_pieces_entry(uint64_t *, uint64_t);
int main(void) {
    uint64_t state = UINT64_C(0x9e3779b97f4a7c15), cells[2] = {0, 0};
    for (unsigned i = 0; i < 10000; ++i) {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        if (private_sret_entry(cells, state) != state || cells[0] != state)
            return 1;
        cells[0] = cells[1] = ~state;
        if (private_pieces_entry(cells, state) != (state ^ (state + 1)) ||
            cells[0] != state || cells[1] != state + 1)
            return 2;
    }
    puts("private indirect and two-word results: 20000 AOT answers pass");
    return 0;
}
