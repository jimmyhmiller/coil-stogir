#include <stdint.h>
#include <assert.h>
#include <stdio.h>
extern uint64_t stogir_recolor(uint64_t *, uint64_t, uint64_t (*)(uint64_t));
static uint64_t callback(uint64_t v) { return v * 3 + 7; }
int main(void) {
    const uint64_t counts[] = {0, 1, 2, 3, 9, 31};
    const uint64_t seeds[] = {0, 17, UINT64_MAX - 255};
    for (unsigned c = 0; c < 6; ++c) for (unsigned s = 0; s < 3; ++s) {
        uint64_t cells[24], expected[24], sum = 0;
        for (unsigned j = 0; j < 24; ++j) cells[j] = expected[j] = seeds[s] + j * 13;
        for (uint64_t i = 0; i < counts[c]; ++i) for (unsigned j = 0; j < 24; ++j) {
            if (i == 1 && j == 0) expected[j] = callback(expected[j]);
            expected[j] += i + j + 1;
        }
        for (unsigned j = 0; j < 24; ++j) sum += expected[j];
        assert(stogir_recolor(cells, counts[c], callback) == sum);
        for (unsigned j = 0; j < 24; ++j) assert(cells[j] == expected[j]);
    }
    puts("recolor C-linked bypass and pressure: pass");
}
