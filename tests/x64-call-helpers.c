/* C side of the tests/x64-call-*.coil tests: functions the generated code
 * calls and drivers that call generated code, compiled by the host C
 * compiler so both directions cross the real System V x86-64 ABI.
 *
 *   tools/x86/call-tests.sh        builds this file on the Linux host and runs
 *                                  the tests with it linked in.
 */
#include <stdarg.h>
#include <stdint.h>
#include <string.h>

/* Memory access for generated code that has no LOAD/STORE of its own. */
int64_t c_load64(const int64_t *p, int64_t i) { return p[i]; }
void c_store64(int64_t *p, int64_t i, int64_t v) { p[i] = v; }
double c_loadf64(const double *p, int64_t i) { return p[i]; }
void c_storef64(double *p, int64_t i, double v) { p[i] = v; }
void c_storef32(float *p, int64_t i, float v) { p[i] = v; }

/* Aggregates by System V class. */
struct pair_ii { int64_t a, b; };              /* INTEGER, INTEGER */
struct pair_dd { double a, b; };               /* SSE, SSE */
struct pair_id { int64_t a; double b; };       /* INTEGER, SSE */
struct pair_di { double a; int64_t b; };       /* SSE, INTEGER */
struct pair_fi { float a; int64_t b; };        /* SSE (one float), INTEGER */
struct big { int64_t a, b, c; };               /* MEMORY */
struct big16 { long double x; int64_t y; };    /* MEMORY, 16-byte aligned */

/* Scalars: more than the six integer and eight vector registers. */
int64_t c_ints10(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e,
                 int64_t f, int64_t g, int64_t h, int64_t i, int64_t j) {
  return a + 2 * b + 3 * c + 4 * d + 5 * e + 6 * f + 7 * g + 8 * h + 9 * i + 10 * j;
}

double c_doubles12(double a, double b, double c, double d, double e, double f,
                   double g, double h, double i, double j, double k, double l) {
  return a + 2 * b + 3 * c + 4 * d + 5 * e + 6 * f + 7 * g + 8 * h + 9 * i +
         10 * j + 11 * k + 12 * l;
}

double c_mixed(int64_t a, double b, int64_t c, double d, float e, int64_t f,
               double g, int64_t h, double i, int64_t j, double k, int64_t l,
               double m, int64_t n, double o, float p, double q, int64_t r) {
  return (double)(a + 3 * c + 5 * f + 7 * h + 11 * j + 13 * l + 17 * n + 19 * r) +
         b + 2 * d + 4 * (double)e + 8 * g + 16 * i + 32 * k + 64 * m + 128 * o +
         256 * (double)p + 512 * q;
}

/* The caller extends narrow integers to 32 bits: these read all 32. */
int64_t c_wide_view(int a, unsigned b, int c, unsigned d, int e, unsigned f) {
  return (int64_t)a + (int64_t)b * 3 + (int64_t)c * 5 + (int64_t)d * 7 +
         (int64_t)e * 11 + (int64_t)f * 13;
}

int8_t c_ret_i8(int64_t v) { return (int8_t)v; }
uint16_t c_ret_u16(int64_t v) { return (uint16_t)v; }

/* Aggregates in registers. */
int64_t c_take_ii(struct pair_ii p, int64_t k) { return p.a * 3 + p.b * 5 + k; }
double c_take_dd(struct pair_dd p, double k) { return p.a * 3 + p.b * 5 + k; }
double c_take_id(struct pair_id p, int64_t k, double m) {
  return (double)(p.a * 3 + k) + p.b * 5 + m * 7;
}
double c_take_di(double m, struct pair_di p, int64_t k) {
  return (double)(p.b * 3 + k) + p.a * 5 + m * 7;
}
double c_take_fi(struct pair_fi p) { return (double)p.a * 2 + (double)p.b; }

/* Five integers leave one integer register: the pair goes to the stack whole
 * and the following integer still takes r9. */
int64_t c_group_stack(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e,
                      struct pair_ii p, int64_t x) {
  return a + 2 * b + 3 * c + 4 * d + 5 * e + 6 * p.a + 7 * p.b + 8 * x;
}

/* Seven doubles leave xmm7. The double pair needs two vector registers, so it
 * goes to the stack whole without using xmm7 up; the mixed pair then takes rdi
 * and xmm7; the last double finds no vector register and goes to the stack. */
double c_group_banks(double a, double b, double c, double d, double e, double f,
                     double g, struct pair_dd p, struct pair_id q, double z) {
  return a + b + c + d + e + f + g + 3 * p.a + 5 * p.b + (double)q.a * 7 + 11 * q.b +
         13 * z;
}

struct pair_ii c_ret_ii(int64_t a, int64_t b) { struct pair_ii r = {a + b, a - b}; return r; }
struct pair_dd c_ret_dd(double a, double b) { struct pair_dd r = {a + b, a - b}; return r; }
struct pair_id c_ret_id(int64_t a, double b) { struct pair_id r = {a * 2, b * 0.5}; return r; }
struct pair_di c_ret_di(int64_t a, double b) { struct pair_di r = {b * 0.25, a * 3}; return r; }

/* MEMORY class: by value on the stack, returned through a hidden pointer. */
struct big c_ret_big(int64_t a, int64_t b) {
  struct big r = {a, b, a * b};
  return r;
}
int64_t c_take_big(int64_t k, struct big v, int64_t l) {
  return k + 2 * v.a + 3 * v.b + 5 * v.c + 7 * l;
}
int64_t c_take_big16(int64_t k, struct big16 v, int64_t l) {
  return k + (int64_t)v.x * 3 + v.y * 5 + 7 * l + (((uintptr_t)&v & 15) == 0 ? 0 : 1000000);
}
/* Seven integer registers' worth, then two aggregates and a stack scalar. */
int64_t c_take_two_big(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e, int64_t f,
                       int64_t g, struct big u, int64_t h, struct big v) {
  return a + b + c + d + e + f + 2 * g + 3 * h + u.a + 2 * u.b + 3 * u.c + 5 * v.a +
         7 * v.b + 11 * v.c;
}
/* A large aggregate, copied by the loop path. */
struct wide { int64_t v[25]; };
int64_t c_take_wide(struct wide w, int64_t k) {
  int64_t sum = k;
  for (int i = 0; i < 25; i++) sum += w.v[i] * (i + 1);
  return sum;
}

/* Variadic callee with integers and doubles in every position class. */
double c_sum_va(int64_t count, ...) {
  va_list ap;
  double sum = 0;
  va_start(ap, count);
  for (int64_t i = 0; i < count; i++) {
    if (i & 1) sum += va_arg(ap, double) * (double)(i + 1);
    else sum += (double)va_arg(ap, int64_t) * (double)(i + 1);
  }
  va_end(ap);
  return sum;
}

/* Drivers: C calls generated code. */
typedef int64_t (*take_ii_fn)(struct pair_ii, int64_t);
int64_t c_drive_take_ii(take_ii_fn f, int64_t a, int64_t b, int64_t k) {
  struct pair_ii p = {a, b};
  return f(p, k);
}
typedef double (*take_id_fn)(struct pair_id, int64_t, double);
double c_drive_take_id(take_id_fn f, int64_t a, double b, int64_t k, double m) {
  struct pair_id p = {a, b};
  return f(p, k, m);
}
typedef int64_t (*group_stack_fn)(int64_t, int64_t, int64_t, int64_t, int64_t,
                                  struct pair_ii, int64_t);
int64_t c_drive_group_stack(group_stack_fn f, int64_t s) {
  struct pair_ii p = {s + 6, s + 7};
  return f(s + 1, s + 2, s + 3, s + 4, s + 5, p, s + 8);
}
typedef struct pair_ii (*ret_ii_fn)(int64_t, int64_t);
int64_t c_drive_ret_ii(ret_ii_fn f, int64_t a, int64_t b) {
  struct pair_ii r = f(a, b);
  return r.a * 7 + r.b * 13;
}
typedef struct pair_dd (*ret_dd_fn)(double, double);
double c_drive_ret_dd(ret_dd_fn f, double a, double b) {
  struct pair_dd r = f(a, b);
  return r.a * 7 + r.b * 13;
}
typedef struct pair_id (*ret_id_fn)(int64_t, double);
double c_drive_ret_id(ret_id_fn f, int64_t a, double b) {
  struct pair_id r = f(a, b);
  return (double)r.a * 7 + r.b * 13;
}
typedef struct pair_di (*ret_di_fn)(int64_t, double);
double c_drive_ret_di(ret_di_fn f, int64_t a, double b) {
  struct pair_di r = f(a, b);
  return r.a * 7 + (double)r.b * 13;
}
typedef struct big (*ret_big_fn)(int64_t, int64_t);
int64_t c_drive_ret_big(ret_big_fn f, int64_t a, int64_t b) {
  struct big r = f(a, b);
  return r.a + 2 * r.b + 3 * r.c;
}
/* The returned rax must be the hidden pointer: read the result through it. */
int64_t c_drive_ret_big_rax(void *f, int64_t a, int64_t b) {
  struct big r;
  struct big *(*raw)(struct big *, int64_t, int64_t) =
      (struct big *(*)(struct big *, int64_t, int64_t))f;
  struct big *returned = raw(&r, a, b);
  return returned == &r ? returned->a + 2 * returned->b + 3 * returned->c : -1;
}
typedef int64_t (*take_big_fn)(int64_t, struct big, int64_t);
int64_t c_drive_take_big(take_big_fn f, int64_t k, int64_t a, int64_t b, int64_t c, int64_t l) {
  struct big v = {a, b, c};
  return f(k, v, l);
}
typedef int64_t (*ints10_fn)(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t,
                             int64_t, int64_t, int64_t, int64_t);
int64_t c_drive_ints10(ints10_fn f, int64_t s) {
  return f(s, s + 1, s + 2, s + 3, s + 4, s + 5, s + 6, s + 7, s + 8, s + 9);
}
typedef double (*doubles12_fn)(double, double, double, double, double, double, double,
                               double, double, double, double, double);
double c_drive_doubles12(doubles12_fn f, double s) {
  return f(s, s + 1, s + 2, s + 3, s + 4, s + 5, s + 6, s + 7, s + 8, s + 9, s + 10, s + 11);
}
/* Narrow arguments with garbage above their width, as a GCC-built caller may
 * leave them: the callee must not trust the upper bits. */
typedef int64_t (*raw6_fn)(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);
int64_t c_drive_dirty(void *f, uint64_t a, uint64_t b, uint64_t c, uint64_t d) {
  return ((raw6_fn)f)(a, b, c, d, 0, 0);
}

/* Raw argument images for tests/x64-call-stress.coil: six general argument
 * registers, eight vector registers (low 64 bits) and 32 stack words.
 * c_inject(f) calls f with every argument location loaded from c_seed;
 * c_capture, called with any signature, stores every argument location in
 * c_frame and returns 12345. */
/* Hidden, so the assembly below may address them PC-relatively even when
 * this object is linked into a shared object. */
__attribute__((visibility("hidden"))) uint64_t c_seed[46];
__attribute__((visibility("hidden"))) uint64_t c_frame[46];
__attribute__((visibility("hidden"))) uint64_t c_frame_rax;
int64_t c_capture(void);
int64_t c_inject(void *f);

__asm__(
    "    .text\n"
    "    .globl c_capture\n"
    "    .type c_capture, @function\n"
    "c_capture:\n"
    "    movq %rax, c_frame_rax(%rip)\n"
    "    movq %rdi, c_frame+0(%rip)\n"
    "    movq %rsi, c_frame+8(%rip)\n"
    "    movq %rdx, c_frame+16(%rip)\n"
    "    movq %rcx, c_frame+24(%rip)\n"
    "    movq %r8, c_frame+32(%rip)\n"
    "    movq %r9, c_frame+40(%rip)\n"
    "    movq %xmm0, c_frame+48(%rip)\n"
    "    movq %xmm1, c_frame+56(%rip)\n"
    "    movq %xmm2, c_frame+64(%rip)\n"
    "    movq %xmm3, c_frame+72(%rip)\n"
    "    movq %xmm4, c_frame+80(%rip)\n"
    "    movq %xmm5, c_frame+88(%rip)\n"
    "    movq %xmm6, c_frame+96(%rip)\n"
    "    movq %xmm7, c_frame+104(%rip)\n"
    "    xorl %ecx, %ecx\n"
    "    leaq c_frame+112(%rip), %rdx\n"
    "1:  movq 8(%rsp,%rcx,8), %rax\n"
    "    movq %rax, (%rdx,%rcx,8)\n"
    "    incq %rcx\n"
    "    cmpq $32, %rcx\n"
    "    jne 1b\n"
    "    movl $12345, %eax\n"
    "    ret\n"
    "    .size c_capture, .-c_capture\n"
    "    .globl c_inject\n"
    "    .type c_inject, @function\n"
    "c_inject:\n"
    "    pushq %rbx\n"
    "    subq $256, %rsp\n"
    "    movq %rdi, %r11\n"
    "    xorl %ecx, %ecx\n"
    "    leaq c_seed+112(%rip), %rdx\n"
    "1:  movq (%rdx,%rcx,8), %rax\n"
    "    movq %rax, (%rsp,%rcx,8)\n"
    "    incq %rcx\n"
    "    cmpq $32, %rcx\n"
    "    jne 1b\n"
    "    movq c_seed+48(%rip), %xmm0\n"
    "    movq c_seed+56(%rip), %xmm1\n"
    "    movq c_seed+64(%rip), %xmm2\n"
    "    movq c_seed+72(%rip), %xmm3\n"
    "    movq c_seed+80(%rip), %xmm4\n"
    "    movq c_seed+88(%rip), %xmm5\n"
    "    movq c_seed+96(%rip), %xmm6\n"
    "    movq c_seed+104(%rip), %xmm7\n"
    "    movq c_seed+0(%rip), %rdi\n"
    "    movq c_seed+8(%rip), %rsi\n"
    "    movq c_seed+16(%rip), %rdx\n"
    "    movq c_seed+24(%rip), %rcx\n"
    "    movq c_seed+32(%rip), %r8\n"
    "    movq c_seed+40(%rip), %r9\n"
    "    call *%r11\n"
    "    addq $256, %rsp\n"
    "    popq %rbx\n"
    "    ret\n"
    "    .size c_inject, .-c_inject\n");

uint64_t *c_seed_words(void) { return c_seed; }
uint64_t *c_frame_words(void) { return c_frame; }
uint64_t c_captured_rax(void) { return c_frame_rax; }
