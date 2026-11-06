#include <stdint.h>
#include <stdio.h>

extern uint64_t private_pressure_entry(uint64_t *, uint64_t);

int main(int argc, char **argv) {
    (void)argv;
    uint64_t cells[32] = {0}, state = UINT64_C(0x9e3779b97f4a7c15);
    for (unsigned turn = 0; turn < 10000; ++turn) {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        for (unsigned i = 0; i < 12; ++i) {
            cells[i] = state * 37 + i * 13;
            cells[i + 16] = 0;
        }
        if (private_pressure_entry(cells, state) != state + 1)
            return 1;
        for (unsigned i = 0; i < 12; ++i)
            if (cells[i] != cells[i + 16])
                return 2;
    }
    uint64_t expected = state;
    if (argc > 1) {
        for (unsigned i = 0; i < 50000000; ++i)
            state = private_pressure_entry(cells, state);
        expected += 50000000;
    }
    if (state != expected)
        return 3;
    uint64_t checksum = state;
    for (unsigned i = 0; i < 12; ++i) {
        if (cells[i] != cells[i + 16])
            return 4;
        checksum ^= cells[i + 16];
    }
    printf("private pressure answers and checksum %llu\n", (unsigned long long)checksum);
    return 0;
}
