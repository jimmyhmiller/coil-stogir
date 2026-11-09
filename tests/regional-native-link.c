#include <assert.h>
#include <stdint.h>
#include <stdio.h>
extern uint64_t stogir_regional_loop(uint64_t *, uint64_t, uint64_t, uint64_t (*)(uint64_t));
static uint64_t callback(uint64_t v) { return v * 3 + 7; }
int main(void) {
    const uint64_t outer[] = {0, 1, 2, 5}, inner[] = {0, 1, 2, 7};
    const uint64_t seeds[] = {0, 17, UINT64_MAX - 255};
    for (unsigned o = 0; o < 4; ++o) for (unsigned n = 0; n < 4; ++n)
        for (unsigned s = 0; s < 3; ++s) {
            uint64_t cells[16], expected[16], y[8], sum = 0;
            for (unsigned j = 0; j < 16; ++j) cells[j] = expected[j] = seeds[s] + j * 13;
            for (uint64_t i = 0; i < outer[o]; ++i) {
                for (unsigned j = 0; j < 8; ++j) y[j] = expected[j + 8] + i;
                for (uint64_t k = 0; k < inner[n]; ++k) for (unsigned j = 0; j < 8; ++j) {
                    if (j == 0) y[j] = callback(y[j]);
                    y[j] += k + j + 1;
                }
                for (unsigned j = 0; j < 8; ++j) expected[j] += y[j];
            }
            for (unsigned j = 0; j < 8; ++j) sum += expected[j];
            assert(stogir_regional_loop(cells, outer[o], inner[n], callback) == sum);
            for (unsigned j = 0; j < 16; ++j) assert(cells[j] == expected[j]);
        }
    puts("regional C-linked nested-loop pressure: pass");
}
