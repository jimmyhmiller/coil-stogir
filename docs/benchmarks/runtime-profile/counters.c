// Diagnostic runtime for a single-threaded counted compiler host on macOS.
// A hint, not MAP_FIXED: never replace an existing mapping.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#define BASE ((void *)UINT64_C(0x500000000000))
#define SIZE (64ULL << 20)
static void dump(void) {
    const char *path = getenv("BBCOUNT_OUT");
    if (!path) return;
    FILE *file = fopen(path, "wb");
    if (!file) { perror("counter output"); abort(); }
    uint64_t *counts = BASE, n = SIZE / sizeof(*counts);
    while (n && !counts[n - 1]) --n;
    if (fwrite(&n, sizeof(n), 1, file) != 1 ||
        fwrite(counts, sizeof(*counts), n, file) != n) {
        perror("counter write"); abort();
    }
    if (fclose(file)) { perror("counter close"); abort(); }
}
__attribute__((constructor)) static void init(void) {
    void *memory = mmap(BASE, SIZE, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANON, -1, 0);
    if (memory != BASE) {
        fprintf(stderr, "counter mapping unavailable: %p\n", memory);
        if (memory != MAP_FAILED) munmap(memory, SIZE);
        abort();
    }
    if (atexit(dump)) abort();
}
