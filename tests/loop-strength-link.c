#include <assert.h>
#include <stdint.h>
#include <string.h>

extern uint64_t stogir_strength_loop(uint64_t *, uint64_t, uint64_t, uint64_t,
                                    uint64_t (*)(uint64_t));
static uint64_t callback(uint64_t value) { return value * 3 + 7; }

int main(void) {
    assert(stogir_strength_loop(0, 0, 99, 5, callback) == 0);
    assert(stogir_strength_loop(0, 3, 0, 5, callback) == 0);
    for (uint64_t count = 0; count <= 3; ++count)
        for (uint64_t stop = 0; stop <= 4; ++stop)
            for (uint64_t trips = 0; trips <= 5; ++trips) {
                uint64_t cells[15], expected[15], sum = 0;
                for (uint64_t k = 0; k != 15; ++k)
                    cells[k] = expected[k] = UINT64_MAX - 8 + k;
                for (uint64_t i = 0; i < count && i < stop; ++i) {
                    for (uint64_t j = 0; j < trips; ++j)
                        sum += callback(expected[i * 5 + j]);
                    expected[i * 5 + 1] = sum;
                }
                assert(stogir_strength_loop(cells, count, stop, trips, callback) == sum);
                assert(memcmp(cells, expected, sizeof cells) == 0);
            }
}
