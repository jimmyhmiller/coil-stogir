#!/usr/bin/env python3
# Prints the expected-result tables of tests/jit-floating-extension.coil.
#
# An independent model of the AArch64 scalar instructions FSQRT, FMADD, FMIN,
# FMAX, FMINNM, FMAXNM and FRINTN/P/M/Z/A: exact rational arithmetic rounded
# once to nearest-even, with the Arm NaN-propagation rules (FPProcessNaNs,
# FPProcessNaNs3, default NaN). No host floating-point operation is used.
#
#   python3 tests/jit-floating-extension-table.py > table.txt
# and replace the block between the GENERATED markers in the test.
from fractions import Fraction
from math import isqrt

MANT = {64: 52, 32: 23}


class Fmt:
    def __init__(self, width):
        self.w = width
        self.m = MANT[width]
        self.ebits = width - 1 - self.m
        self.bias = (1 << (self.ebits - 1)) - 1
        self.sign = 1 << (width - 1)
        self.inf = ((1 << self.ebits) - 1) << self.m
        self.quiet = 1 << (self.m - 1)
        self.default_nan = self.inf | self.quiet

    def is_nan(self, b):
        return (b & ~self.sign) > self.inf

    def is_snan(self, b):
        return self.is_nan(b) and not (b & self.quiet)

    def is_inf(self, b):
        return (b & ~self.sign) == self.inf

    def is_zero(self, b):
        return (b & ~self.sign) == 0

    def neg(self, b):
        return bool(b & self.sign)

    def value(self, b):
        mag = b & ~self.sign
        e = mag >> self.m
        f = mag & ((1 << self.m) - 1)
        if e == 0:
            v = Fraction(f) * Fraction(2) ** (1 - self.bias - self.m)
        else:
            v = Fraction(f | (1 << self.m)) * Fraction(2) ** (e - self.bias - self.m)
        return -v if self.neg(b) else v

    def encode(self, v, zero_negative=False):
        """Round the exact rational V to nearest, ties to even."""
        if v == 0:
            return self.sign if zero_negative else 0
        s = self.sign if v < 0 else 0
        a = abs(v)
        # exponent of the leading bit
        e = a.numerator.bit_length() - a.denominator.bit_length()
        if Fraction(2) ** e > a:
            e -= 1
        e = max(e, 1 - self.bias)  # subnormals share the minimum exponent
        scaled = a / Fraction(2) ** (e - self.m)  # units of the last place
        n = scaled.numerator // scaled.denominator
        rest = scaled - n
        if rest > Fraction(1, 2) or (rest == Fraction(1, 2) and n & 1):
            n += 1
        if n >= 1 << (self.m + 1):
            n >>= 1
            e += 1
        if e > self.bias:
            return s | self.inf
        if n < 1 << self.m:  # subnormal
            return s | n
        return s | ((e + self.bias) << self.m) | (n - (1 << self.m))

    def nans2(self, a, b):
        if self.is_snan(a):
            return a | self.quiet
        if self.is_snan(b):
            return b | self.quiet
        if self.is_nan(a):
            return a
        if self.is_nan(b):
            return b
        return None

    def sqrt(self, a):
        if self.is_nan(a):
            return a | self.quiet
        if self.is_zero(a):
            return a
        if self.neg(a):
            return self.default_nan
        if self.is_inf(a):
            return a
        v = self.value(a)
        # 4^k clears every denominator (at most 2^1126) and leaves the root
        # with far more bits than a significand.
        k = 1200
        scaled = v * Fraction(4) ** k
        assert scaled.denominator == 1
        n = scaled.numerator
        r = isqrt(n)
        exact = r * r == n
        # An inexact root is never a rounding midpoint; any point strictly
        # between r and r+1 rounds as the root does.
        approx = Fraction(r) if exact else Fraction(2 * r + 1, 2)
        return self.encode(approx / Fraction(2) ** k)

    def minmax(self, op, a, b):
        number = op in ("fminnm", "fmaxnm")
        if number:
            qa = self.is_nan(a) and not self.is_snan(a)
            qb = self.is_nan(b) and not self.is_snan(b)
            if qa and not self.is_nan(b):
                return b
            if qb and not self.is_nan(a):
                return a
            if qa and self.is_snan(b):
                return b | self.quiet
            if qb and self.is_snan(a):
                return a | self.quiet
        n = self.nans2(a, b)
        if n is not None:
            return n
        minimum = op in ("fmin", "fminnm")

        def key(x):
            if self.is_inf(x):
                return (-1 if self.neg(x) else 1, 0)
            return (0, self.value(x))

        ka, kb = key(a), key(b)
        if ka == kb:  # equal: only the zeros differ in bits
            return (a | b) if minimum else (a & b)
        return a if (ka < kb) == minimum else b

    def rint(self, op, a):
        if self.is_nan(a):
            return a | self.quiet
        if self.is_inf(a) or self.is_zero(a):
            return a
        v = self.value(a)
        floor = v.numerator // v.denominator
        rest = v - floor
        if rest == 0:
            n = floor
        elif op == "frintm":
            n = floor
        elif op == "frintp":
            n = floor + 1
        elif op == "frintz":
            n = floor if v > 0 else floor + 1
        elif op == "frinta":
            if rest == Fraction(1, 2):
                n = floor + 1 if v > 0 else floor
            else:
                n = floor + 1 if rest > Fraction(1, 2) else floor
        else:
            if rest == Fraction(1, 2):
                n = floor + (floor & 1)
            else:
                n = floor + 1 if rest > Fraction(1, 2) else floor
        return self.encode(Fraction(n), self.neg(a))

    def fma(self, a, b, c):
        """a * b + c, the FMADD result with addend c."""
        inf_zero = (self.is_inf(a) and self.is_zero(b)) or (
            self.is_zero(a) and self.is_inf(b)
        )
        if self.is_nan(c) and not self.is_snan(c) and inf_zero:
            return self.default_nan
        for x in (c, a, b):
            if self.is_snan(x):
                return x | self.quiet
        for x in (c, a, b):
            if self.is_nan(x):
                return x
        if inf_zero:
            return self.default_nan
        product_negative = self.neg(a) != self.neg(b)
        if self.is_inf(a) or self.is_inf(b):
            if self.is_inf(c) and self.neg(c) != product_negative:
                return self.default_nan
            return self.inf | (self.sign if product_negative else 0)
        if self.is_inf(c):
            return c
        product = self.value(a) * self.value(b)
        total = product + self.value(c)
        if total == 0:
            if product == 0 and self.is_zero(c):
                return self.sign if (product_negative and self.neg(c)) else 0
            if product == 0:
                return c
            return 0
        return self.encode(total)


# name: (f64 bits, f32 bits). The first nine feed FMA, the first sixteen the
# binary operations, all of them the unary ones.
PATTERNS = [
    (0x0000000000000000, 0x00000000),  # +0
    (0x8000000000000000, 0x80000000),  # -0
    (0x3FF0000000000000, 0x3F800000),  # 1
    (0x3FF0000004000000, 0x3F800800),  # 1 + 2^-30 | 1 + 2^-12
    (0xBFF0000008000000, 0xBF801000),  # -(1 + 2^-29) | -(1 + 2^-11)
    (0x7FF0000000000000, 0x7F800000),  # +inf
    (0x7FF8123456789ABC, 0x7FC12345),  # quiet NaN with a payload
    (0x7FF0123456789ABC, 0x7F812345),  # signalling NaN
    (0xC008000000000000, 0xC0400000),  # -3
    (0xFFF0000000000000, 0xFF800000),  # -inf
    (0x0000000000000001, 0x00000001),  # least subnormal
    (0x8000000000000001, 0x80000001),  # -least subnormal
    (0x7FEFFFFFFFFFFFFF, 0x7F7FFFFF),  # greatest finite
    (0x4000000000000000, 0x40000000),  # 2
    (0xBFF0000000000000, 0xBF800000),  # -1
    (0xFFF8000000000001, 0xFFC00001),  # negative quiet NaN
    (0x3FE0000000000000, 0x3F000000),  # 0.5
    (0xBFE0000000000000, 0xBF000000),  # -0.5
    (0x3FF8000000000000, 0x3FC00000),  # 1.5
    (0x4004000000000000, 0x40200000),  # 2.5
    (0xC004000000000000, 0xC0200000),  # -2.5
    (0x400C000000000000, 0x40600000),  # 3.5
    (0xBFF8000000000000, 0xBFC00000),  # -1.5
    (0x3FE8000000000000, 0x3F400000),  # 0.75
    (0xBFE8000000000000, 0xBF400000),  # -0.75
    (0x3FD0000000000000, 0x3E800000),  # 0.25
    (0x3FDFFFFFFFFFFFFF, 0x3EFFFFFF),  # just below 0.5
    (0x3FE0000000000001, 0x3F000001),  # just above 0.5
    (0x432FFFFFFFFFFFFF, 0x4AFFFFFF),  # 2^52 - 0.5 | 2^23 - 0.5
    (0x4330000000000001, 0x4B000001),  # 2^52 + 1 | 2^23 + 1
    (0x4340000000000000, 0x4B800000),  # 2^53 | 2^24
    (0x4010000000000000, 0x40800000),  # 4
    (0x400921FB54442D18, 0x40490FDB),  # pi
    (0x000FFFFFFFFFFFFF, 0x007FFFFF),  # greatest subnormal
    (0x0010000000000000, 0x00800000),  # least normal
    (0x7E37E43C8800759C, 0x7149F2CA),  # 1e300 | 1e30
]
TERNARY = 9
BINARY = 16
UNARY_OPS = ["fsqrt", "frintn", "frintp", "frintm", "frintz", "frinta"]
BINARY_OPS = ["fmin", "fmax", "fminnm", "fmaxnm"]


def table(name, values):
    print("(def %s" % name)
    for i, v in enumerate(values):
        head = "  [(: 0x%X u64)" % v if i == 0 else "   0x%X" % v
        print(head + ("])" if i == len(values) - 1 else ""))
    print()


def main():
    print("(const PATTERN-COUNT %d)" % len(PATTERNS))
    print()
    print("(const BINARY-COUNT %d)" % BINARY)
    print()
    print("(const TERNARY-COUNT %d)" % TERNARY)
    print()
    for width, label, column in ((64, "WIDE", 0), (32, "NARROW", 1)):
        f = Fmt(width)
        p = [x[column] for x in PATTERNS]
        table("%s-PATTERNS" % label, p)
        unary = []
        for op in UNARY_OPS:
            for a in p:
                unary.append(f.sqrt(a) if op == "fsqrt" else f.rint(op, a))
        table("%s-UNARY" % label, unary)
        binary = []
        for op in BINARY_OPS:
            for a in p[:BINARY]:
                for b in p[:BINARY]:
                    binary.append(f.minmax(op, a, b))
        table("%s-BINARY" % label, binary)
        ternary = []
        for a in p[:TERNARY]:
            for b in p[:TERNARY]:
                for c in p[:TERNARY]:
                    ternary.append(f.fma(a, b, c))
        table("%s-TERNARY" % label, ternary)


main()
