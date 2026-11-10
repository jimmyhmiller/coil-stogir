"""Case list for the x86-64 encoder test; see gen-encode-cases.py.

Each case pairs an encoder call with the Intel-syntax instruction it must
encode. Where the encoder deliberately picks a shorter encoding than llvm-mc
would for the literal text, the assembly names the instruction actually
emitted (noted at each such place).
"""

R64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
       "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
R32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"] + ["r%dd" % n for n in range(8, 16)]
R16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"] + ["r%dw" % n for n in range(8, 16)]
R8 = ["al", "cl", "dl", "bl", "spl", "bpl", "sil", "dil"] + ["r%db" % n for n in range(8, 16)]
NAMES = {8: R8, 16: R16, 32: R32, 64: R64}
PTR = {8: "byte ptr", 16: "word ptr", 32: "dword ptr", 64: "qword ptr", 128: "xmmword ptr"}
BITS = [8, 16, 32, 64]
WIDE = [16, 32, 64]

CC = ["o", "no", "b", "ae", "e", "ne", "be", "a", "s", "ns", "p", "np", "l", "ge", "le", "g"]

# Registers with an encoding corner: rsp/r12 (SIB as base), rbp/r13 (no mod=00
# base), rsi/rdi (REX for the byte register), r8.. (REX extension bits).
REGS = [0, 1, 4, 5, 6, 7, 8, 12, 13, 15]

RIP_DISP = 0x11223344
RIP_FIELD = "44332211"


def reg(bits, number):
    return NAMES[bits][number]


def xmm(number):
    return "xmm%d" % number


class M:
    """A memory operand: base/index are register numbers, None, or "rip"."""

    def __init__(self, base, disp=0, index=None, scale=1):
        self.base, self.disp, self.index, self.scale = base, disp, index, scale

    def coil(self):
        if self.base == "rip":
            return "(e/mem-rip %d)" % self.disp
        if self.index is not None:
            return "(e/mem-index %d %d %d %d)" % (
                -1 if self.base is None else self.base, self.index, self.scale, self.disp)
        if self.base is None:
            return "(e/mem-absolute %d)" % self.disp
        return "(e/mem %d %d)" % (self.base, self.disp)

    def asm(self, bits=None):
        parts = []
        if self.base == "rip":
            parts.append("rip")
        elif self.base is not None:
            parts.append(R64[self.base])
        if self.index is not None:
            parts.append("%s*%d" % (R64[self.index], self.scale))
        text = " + ".join(parts)
        if self.disp or not parts:
            if not parts:
                text = "%d" % self.disp
            elif self.disp < 0:
                text += " - %d" % -self.disp
            else:
                text += " + %d" % self.disp
        prefix = PTR[bits] + " " if bits else ""
        return "%s[%s]" % (prefix, text)

    @property
    def field(self):
        return RIP_FIELD if self.base == "rip" else None


def full_mems():
    """Every addressing-mode corner."""
    mems = []
    for base in REGS:
        mems.append(M(base))
    for base in [0, 4, 5, 12, 13]:
        for disp in [1, 127, -128, 128, -129, 0x12345678, -0x80000000, 0x7FFFFFFF]:
            mems.append(M(base, disp))
    for base in [0, 4, 5, 8, 12, 13]:
        for index in [0, 1, 5, 8, 12, 13, 15]:
            scale = [1, 2, 4, 8][(base + index) % 4]
            mems.append(M(base, 0, index, scale))
    for scale in [1, 2, 4, 8]:
        mems.append(M(1, 0, 2, scale))
        mems.append(M(5, 8, 13, scale))
        mems.append(M(13, -8, 5, scale))
        mems.append(M(4, 0x1000, 12, scale))
        mems.append(M(12, -0x1000, 15, scale))
        mems.append(M(None, 0x10, 1, scale))
        mems.append(M(None, 0, 13, scale))
    mems.append(M(None, 0x10))
    mems.append(M(None, -8))
    mems.append(M(None, 0x12345678))
    mems.append(M("rip", RIP_DISP))
    mems.append(M("rip", -RIP_DISP))
    return mems


# A representative handful for the instructions whose operand encoding is the
# shared path already swept by `full_mems`.
SMALL = [M(0), M(4, 8), M(5), M(13, 0x100, 1, 4), M(12, -8, 15, 8), M("rip", RIP_DISP)]


def cases():
    out = []

    def add(expr, asm, field=None):
        out.append((expr, asm, field))

    def rip_field(m):
        if m.base != "rip":
            return None
        return (m.disp & 0xFFFFFFFF).to_bytes(4, "little").hex()

    def small(i):
        return SMALL[i % len(SMALL)]

    pairs = [(0, 1), (1, 0), (4, 5), (5, 4), (6, 7), (7, 6), (8, 0), (0, 8),
             (12, 13), (13, 12), (15, 15), (3, 9), (4, 12), (13, 5)]

    # --- moves -----------------------------------------------------------
    for bits in BITS:
        for d, s in pairs:
            add("(e/mov-rr $ %d %d %d)" % (bits, d, s),
                "mov %s, %s" % (reg(bits, d), reg(bits, s)))
    for i, m in enumerate(full_mems()):
        r = REGS[i % len(REGS)]
        add("(e/mov-rm $ 64 %d %s)" % (r, m.coil()),
            "mov %s, %s" % (reg(64, r), m.asm(64)), rip_field(m))
        add("(e/mov-mr $ 32 %s %d)" % (m.coil(), r),
            "mov %s, %s" % (m.asm(32), reg(32, r)), rip_field(m))
    for bits in [8, 16, 32]:
        for i, m in enumerate(SMALL):
            r = [0, 6, 4, 9, 7, 13][i]
            add("(e/mov-rm $ %d %d %s)" % (bits, r, m.coil()),
                "mov %s, %s" % (reg(bits, r), m.asm(bits)), m.field)
    for bits in [8, 16, 64]:
        for i, m in enumerate(SMALL):
            r = [0, 6, 5, 9, 7, 13][i]
            add("(e/mov-mr $ %d %s %d)" % (bits, m.coil(), r),
                "mov %s, %s" % (m.asm(bits), reg(bits, r)), m.field)

    for r, v in [(0, 0x12), (1, -1), (6, 255), (4, 0), (7, -128), (9, 0x7F), (15, 1)]:
        add("(e/mov-ri $ 8 %d %d)" % (r, v), "mov %s, %d" % (reg(8, r), v))
    for r, v in [(0, 0x1234), (1, -1), (9, 65535), (5, 0)]:
        add("(e/mov-ri $ 16 %d %d)" % (r, v), "mov %s, %d" % (reg(16, r), v))
    for r, v in [(0, 0), (1, 0x12345678), (7, 0xFFFFFFFF), (8, -1), (15, 0x80000000),
                 (4, 1), (13, -0x80000000)]:
        add("(e/mov-ri $ 32 %d %d)" % (r, v), "mov %s, %d" % (reg(32, r), v))
    # A 64-bit constant that fits unsigned 32 bits is the 32-bit move (llvm-mc
    # would spell `mov rax, 1` as the 7-byte sign-extended form).
    for r, v in [(0, 0), (1, 1), (2, 0x7FFFFFFF), (9, 0xFFFFFFFF), (15, 0x80000000), (4, 5)]:
        add("(e/mov-ri $ 64 %d %d)" % (r, v), "mov %s, %d" % (reg(32, r), v))
    for r, v in [(0, -1), (1, -0x80000000), (12, -2), (5, -129)]:
        add("(e/mov-ri $ 64 %d %d)" % (r, v), "mov %s, %d" % (reg(64, r), v))
    for r, v in [(0, 0x100000000), (1, 0x1122334455667788), (8, -0x80000001),
                 (15, 0x7FFFFFFFFFFFFFFF), (4, -0x8000000000000000), (13, 0xFFFFFFFF + 1)]:
        add("(e/mov-ri $ 64 %d %d)" % (r, v), "movabs %s, %d" % (reg(64, r), v), -8)
    for r, v in [(0, 0), (1, 1), (9, -1), (12, 0x1122334455667788), (5, 0x12345678)]:
        add("(e/movabs-ri $ %d %d)" % (r, v), "movabs %s, %d" % (reg(64, r), v), -8)

    for i, m in enumerate(SMALL):
        for bits, v in [(8, 0x7F), (8, -1), (16, 0x1234), (16, -1), (32, 0x12345678),
                        (32, -1), (64, 0x12345678), (64, -1)]:
            add("(e/mov-mi $ %d %s %d)" % (bits, m.coil(), v),
                "mov %s, %d" % (m.asm(bits), v), m.field)

    for r in [0, 1, 6, 7, 8, 12, 15]:
        add("(e/zero-r $ %d)" % r, "xor %s, %s" % (reg(32, r), reg(32, r)))

    sources = {8: [0, 1, 4, 5, 6, 7, 8, 13], 16: [0, 1, 4, 6, 9, 13], 32: [0, 1, 4, 9, 13]}
    for dst_bits, src_bits in [(16, 8), (32, 8), (64, 8), (32, 16), (64, 16)]:
        # A 64-bit zero extension is the 32-bit form.
        asm_bits = 32 if dst_bits == 64 else dst_bits
        for i, s in enumerate(sources[src_bits]):
            d = REGS[(i * 3 + 1) % len(REGS)]
            add("(e/movzx-rr $ %d %d %d %d)" % (dst_bits, src_bits, d, s),
                "movzx %s, %s" % (reg(asm_bits, d), reg(src_bits, s)))
        for i, m in enumerate(SMALL):
            d = REGS[(i * 3 + 2) % len(REGS)]
            add("(e/movzx-rm $ %d %d %d %s)" % (dst_bits, src_bits, d, m.coil()),
                "movzx %s, %s" % (reg(asm_bits, d), m.asm(src_bits)), m.field)
    for i, s in enumerate(sources[32]):
        d = REGS[(i * 3 + 1) % len(REGS)]
        add("(e/movzx-rr $ 64 32 %d %d)" % (d, s), "mov %s, %s" % (reg(32, d), reg(32, s)))
    for i, m in enumerate(SMALL):
        d = REGS[(i * 3 + 2) % len(REGS)]
        add("(e/movzx-rm $ 64 32 %d %s)" % (d, m.coil()),
            "mov %s, %s" % (reg(32, d), m.asm(32)), m.field)
    for dst_bits, src_bits in [(16, 8), (32, 8), (64, 8), (32, 16), (64, 16), (64, 32)]:
        name = "movsxd" if src_bits == 32 else "movsx"
        for i, s in enumerate(sources[src_bits]):
            d = REGS[(i * 3 + 1) % len(REGS)]
            add("(e/movsx-rr $ %d %d %d %d)" % (dst_bits, src_bits, d, s),
                "%s %s, %s" % (name, reg(dst_bits, d), reg(src_bits, s)))
        for i, m in enumerate(SMALL):
            d = REGS[(i * 3 + 2) % len(REGS)]
            add("(e/movsx-rm $ %d %d %d %s)" % (dst_bits, src_bits, d, m.coil()),
                "%s %s, %s" % (name, reg(dst_bits, d), m.asm(src_bits)), m.field)

    for i, m in enumerate(full_mems()):
        if m.base is None and m.index is None:
            continue
        r = REGS[(i * 7 + 3) % len(REGS)]
        add("(e/lea $ 64 %d %s)" % (r, m.coil()),
            "lea %s, %s" % (reg(64, r), m.asm()), rip_field(m))
    for i, m in enumerate(SMALL):
        r = REGS[(i * 7 + 3) % len(REGS)]
        add("(e/lea $ 32 %d %s)" % (r, m.coil()), "lea %s, %s" % (reg(32, r), m.asm()), m.field)

    for a, b in [(0, 1), (6, 7), (4, 5), (9, 0), (12, 13)]:
        add("(e/xchg-rr $ 8 %d %d)" % (a, b), "xchg %s, %s" % (reg(8, a), reg(8, b)))
    for bits in WIDE:
        for a, b in [(1, 2), (0, 1), (1, 0), (8, 0), (0, 15), (12, 13), (5, 4), (3, 3)]:
            add("(e/xchg-rr $ %d %d %d)" % (bits, a, b),
                "xchg %s, %s" % (reg(bits, a), reg(bits, b)))
    add("(e/xchg-rr $ 32 0 0)", "xchg eax, eax")
    add("(e/xchg-rr $ 16 0 0)", "xchg ax, ax")
    add("(e/xchg-rr $ 64 0 0)", "xchg rax, rax")
    for i, m in enumerate(SMALL):
        for bits in BITS:
            r = [1, 6, 0, 12, 7, 9][i]
            add("(e/xchg-rm $ %d %d %s)" % (bits, r, m.coil()),
                "xchg %s, %s" % (reg(bits, r), m.asm(bits)), m.field)
    for bits in [32, 64]:
        for r in REGS:
            add("(e/bswap $ %d %d)" % (bits, r), "bswap %s" % reg(bits, r))

    # --- arithmetic and logic -------------------------------------------
    alu = ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"]
    for op, name in enumerate(alu):
        const = "e/" + name.upper()
        for bits in BITS:
            for d, s in [(0, 1), (6, 12), (4, 7), (13, 5), (8, 8)]:
                add("(e/alu-rr $ %s %d %d %d)" % (const, bits, d, s),
                    "%s %s, %s" % (name, reg(bits, d), reg(bits, s)))
        for i, m in enumerate(SMALL):
            bits = BITS[(i + op) % 4]
            r = [0, 7, 12, 5, 9, 1][i]
            add("(e/alu-rm $ %s %d %d %s)" % (const, bits, r, m.coil()),
                "%s %s, %s" % (name, reg(bits, r), m.asm(bits)), m.field)
            bits = BITS[(i + op + 2) % 4]
            add("(e/alu-mr $ %s %d %s %d)" % (const, bits, m.coil(), r),
                "%s %s, %s" % (name, m.asm(bits), reg(bits, r)), m.field)
        immediates = [
            (8, 0, 1), (8, 1, 0x7F), (8, 6, -1), (8, 4, 0x80), (8, 9, 255), (8, 0, -128),
            (16, 0, 0x1234), (16, 0, 1), (16, 1, 0x1234), (16, 12, -1), (16, 5, 0xFFFF),
            (16, 0, 0x80), (16, 2, -129),
            (32, 0, 1), (32, 0, 0x12345678), (32, 1, 0x12345678), (32, 1, -1),
            (32, 9, 127), (32, 9, 128), (32, 4, -128), (32, 13, -129), (32, 0, 0x80),
            (64, 0, 0x12345678), (64, 0, 1), (64, 1, -129), (64, 12, 127), (64, 12, -128),
            (64, 4, 8), (64, 5, 128), (64, 15, -0x80000000), (64, 13, 0x7FFFFFFF),
        ]
        for bits, r, v in immediates:
            add("(e/alu-ri $ %s %d %d %d)" % (const, bits, r, v),
                "%s %s, %d" % (name, reg(bits, r), v))
        # An unsigned spelling of a negative value takes the sign-extended imm8.
        add("(e/alu-ri $ %s 32 1 4294967295)" % const, "%s ecx, -1" % name)
        add("(e/alu-ri $ %s 16 1 65535)" % const, "%s cx, -1" % name)
        for i, m in enumerate(SMALL):
            for bits, v in [(8, 5), (16, 0x1234), (32, 5), (32, 0x12345678), (64, -5),
                            (64, 0x12345678), (16, -1)]:
                add("(e/alu-mi $ %s %d %s %d)" % (const, bits, m.coil(), v),
                    "%s %s, %d" % (name, m.asm(bits), v), m.field)

    for bits in BITS:
        for a, b in [(0, 1), (1, 0), (6, 7), (4, 12), (13, 5), (8, 15)]:
            add("(e/test-rr $ %d %d %d)" % (bits, a, b),
                "test %s, %s" % (reg(bits, a), reg(bits, b)))
        for i, m in enumerate(SMALL):
            r = [0, 6, 4, 9, 7, 13][i]
            add("(e/test-mr $ %d %s %d)" % (bits, m.coil(), r),
                "test %s, %s" % (m.asm(bits), reg(bits, r)), m.field)
    for bits, r, v in [(8, 0, 1), (8, 1, 0x80), (8, 6, -1), (8, 7, 0x7F), (8, 9, 255),
                       (16, 0, 0x1234), (16, 1, 1), (16, 13, -1),
                       (32, 0, 1), (32, 1, 1), (32, 0, 0x12345678), (32, 12, -1),
                       (32, 5, 0x80000000),
                       (64, 0, -1), (64, 1, -1), (64, 12, -0x80000000), (64, 4, -5)]:
        add("(e/test-ri $ %d %d %d)" % (bits, r, v), "test %s, %d" % (reg(bits, r), v))
    # A 64-bit test against a value below 2^31 is the 32-bit test.
    for r, v in [(0, 1), (1, 1), (0, 0x7FFFFFFF), (9, 0x12345678), (6, 0x80), (13, 0)]:
        add("(e/test-ri $ 64 %d %d)" % (r, v), "test %s, %d" % (reg(32, r), v))
    for i, m in enumerate(SMALL):
        for bits, v in [(8, 1), (8, -1), (16, 0x1234), (32, 1), (32, 0x12345678), (64, 1),
                        (64, -1)]:
            add("(e/test-mi $ %d %s %d)" % (bits, m.coil(), v),
                "test %s, %d" % (m.asm(bits), v), m.field)

    unary = ["not", "neg", "mul", "imul", "div", "idiv", "inc", "dec"]
    for name in unary:
        const = "e/" + name.upper()
        for bits in BITS:
            for r in [0, 1, 4, 6, 7, 9, 13]:
                add("(e/unary-r $ %s %d %d)" % (const, bits, r), "%s %s" % (name, reg(bits, r)))
        for i, m in enumerate(SMALL):
            for bits in BITS:
                add("(e/unary-m $ %s %d %s)" % (const, bits, m.coil()),
                    "%s %s" % (name, m.asm(bits)), m.field)

    for bits in WIDE:
        for d, s in [(0, 1), (1, 0), (12, 5), (5, 12), (15, 15), (4, 13)]:
            add("(e/imul-rr $ %d %d %d)" % (bits, d, s),
                "imul %s, %s" % (reg(bits, d), reg(bits, s)))
        for i, m in enumerate(SMALL):
            d = [0, 6, 4, 9, 7, 13][i]
            add("(e/imul-rm $ %d %d %s)" % (bits, d, m.coil()),
                "imul %s, %s" % (reg(bits, d), m.asm(bits)), m.field)
        big = 0x1234 if bits == 16 else 0x12345678
        for d, s, v in [(0, 1, 5), (1, 0, -5), (12, 5, 127), (5, 12, -128), (0, 0, 128),
                        (9, 13, -129), (4, 4, big), (15, 1, -big)]:
            add("(e/imul-rri $ %d %d %d %d)" % (bits, d, s, v),
                "imul %s, %s, %d" % (reg(bits, d), reg(bits, s), v))
        for i, m in enumerate(SMALL):
            d = [0, 6, 4, 9, 7, 13][i]
            for v in [5, big]:
                add("(e/imul-rmi $ %d %d %s %d)" % (bits, d, m.coil(), v),
                    "imul %s, %s, %d" % (reg(bits, d), m.asm(bits), v), m.field)
    add("(e/sign-extend-rax-rdx $ 16)", "cwd")
    add("(e/sign-extend-rax-rdx $ 32)", "cdq")
    add("(e/sign-extend-rax-rdx $ 64)", "cqo")
    add("(e/cdq $)", "cdq")
    add("(e/cqo $)", "cqo")

    # --- shifts, rotates, bit operations --------------------------------
    for name in ["rol", "ror", "rcl", "rcr", "shl", "shr", "sar"]:
        const = "e/" + name.upper()
        for bits in BITS:
            for r, count in [(0, 1), (1, 2), (6, bits - 1), (12, 1), (5, 5), (13, 0)]:
                add("(e/shift-ri $ %s %d %d %d)" % (const, bits, r, count),
                    "%s %s, %d" % (name, reg(bits, r), count))
            for r in [0, 1, 7, 12]:
                add("(e/shift-rc $ %s %d %d)" % (const, bits, r),
                    "%s %s, cl" % (name, reg(bits, r)))
        for i, m in enumerate(SMALL):
            bits = BITS[i % 4]
            for count in [1, 3]:
                add("(e/shift-mi $ %s %d %s %d)" % (const, bits, m.coil(), count),
                    "%s %s, %d" % (name, m.asm(bits), count), m.field)
            add("(e/shift-mc $ %s %d %s)" % (const, bits, m.coil()),
                "%s %s, cl" % (name, m.asm(bits)), m.field)
    for name in ["shld", "shrd"]:
        for bits in WIDE:
            for d, s in [(0, 1), (1, 0), (12, 5), (5, 13), (15, 8)]:
                add("(e/%s-rri $ %d %d %d %d)" % (name, bits, d, s, bits - 3),
                    "%s %s, %s, %d" % (name, reg(bits, d), reg(bits, s), bits - 3))
                add("(e/%s-rrc $ %d %d %d)" % (name, bits, d, s),
                    "%s %s, %s, cl" % (name, reg(bits, d), reg(bits, s)))

    for name in ["bt", "bts", "btr", "btc"]:
        const = "e/" + name.upper()
        for bits in WIDE:
            for r, index in [(0, 0), (1, bits - 1), (12, 5), (5, 7)]:
                add("(e/bt-ri $ %s %d %d %d)" % (const, bits, r, index),
                    "%s %s, %d" % (name, reg(bits, r), index))
            for r, index in [(0, 1), (1, 0), (12, 5), (5, 13), (15, 8)]:
                add("(e/bt-rr $ %s %d %d %d)" % (const, bits, r, index),
                    "%s %s, %s" % (name, reg(bits, r), reg(bits, index)))
        for i, m in enumerate(SMALL):
            bits = WIDE[i % 3]
            add("(e/bt-mi $ %s %d %s %d)" % (const, bits, m.coil(), 7),
                "%s %s, 7" % (name, m.asm(bits)), m.field)
            r = [0, 6, 4, 9, 7, 13][i]
            add("(e/bt-mr $ %s %d %s %d)" % (const, bits, m.coil(), r),
                "%s %s, %s" % (name, m.asm(bits), reg(bits, r)), m.field)

    for name in ["bsf", "bsr", "tzcnt", "lzcnt", "popcnt"]:
        const = "e/" + name.upper()
        for bits in WIDE:
            for d, s in [(0, 1), (1, 0), (12, 5), (5, 13), (15, 8)]:
                add("(e/scan-rr $ %s %d %d %d)" % (const, bits, d, s),
                    "%s %s, %s" % (name, reg(bits, d), reg(bits, s)))
        for i, m in enumerate(SMALL):
            bits = WIDE[i % 3]
            d = [0, 6, 4, 9, 7, 13][i]
            add("(e/scan-rm $ %s %d %d %s)" % (const, bits, d, m.coil()),
                "%s %s, %s" % (name, reg(bits, d), m.asm(bits)), m.field)

    # --- conditions ------------------------------------------------------
    for cc, name in enumerate(CC):
        const = "e/CC-" + name.upper()
        for r in [0, 1, 4, 5, 6, 7, 8, 13]:
            add("(e/setcc-r $ %s %d)" % (const, r), "set%s %s" % (name, reg(8, r)))
        m = small(cc)
        add("(e/setcc-m $ %s %s)" % (const, m.coil()), "set%s %s" % (name, m.asm(8)), m.field)
        for i, bits in enumerate(WIDE):
            d, s = [(0, 1), (12, 5), (5, 13), (9, 0)][(cc + i) % 4]
            add("(e/cmov-rr $ %s %d %d %d)" % (const, bits, d, s),
                "cmov%s %s, %s" % (name, reg(bits, d), reg(bits, s)))
            m = small(cc + i)
            add("(e/cmov-rm $ %s %d %d %s)" % (const, bits, d, m.coil()),
                "cmov%s %s, %s" % (name, reg(bits, d), m.asm(bits)), m.field)
        add("(e/jcc-rel8 $ %s 16)" % const, "j%s {L}+2+16" % name, -1)
        add("(e/jcc-rel8 $ %s -128)" % const, "j%s {L}+2-128" % name, -1)
        add("(e/jcc-rel8 $ %s 127)" % const, "j%s {L}+2+127" % name, -1)
        add("(e/jcc-rel32 $ %s 305419896)" % const, "j%s {L}+6+305419896" % name, -4)
        # Backward, the nearest target llvm-mc cannot reach with the short form.
        add("(e/jcc-rel32 $ %s -133)" % const, "j%s {L}+6-133" % name, -4)
        add("(e/jcc-rel32 $ %s 128)" % const, "j%s {L}+6+128" % name, -4)

    # --- stack and control flow -----------------------------------------
    for r in range(16):
        add("(e/push-r $ %d)" % r, "push %s" % reg(64, r))
        add("(e/pop-r $ %d)" % r, "pop %s" % reg(64, r))
        add("(e/call-r $ %d)" % r, "call %s" % reg(64, r))
        add("(e/jmp-r $ %d)" % r, "jmp %s" % reg(64, r))
    for m in SMALL + [M(12), M(13), M(None, 0x1000, 1, 8)]:
        add("(e/push-m $ %s)" % m.coil(), "push %s" % m.asm(64), m.field)
        add("(e/pop-m $ %s)" % m.coil(), "pop %s" % m.asm(64), m.field)
        add("(e/call-m $ %s)" % m.coil(), "call %s" % m.asm(64), m.field)
        add("(e/jmp-m $ %s)" % m.coil(), "jmp %s" % m.asm(64), m.field)
    for v in [0, 5, -1, 127, -128, 128, -129, 0x12345678, -0x80000000, 0x7FFFFFFF]:
        add("(e/push-i $ %d)" % v, "push %d" % v)
    for rel in [0, 4096, -4096, 0x12345678, -0x80000000, 0x7FFFFFFF, -5]:
        add("(e/call-rel32 $ %d)" % rel, "call {L}+5%+d" % rel, -4)
    for rel in [0, 16, 127, -128, -2]:
        add("(e/jmp-rel8 $ %d)" % rel, "jmp {L}+2%+d" % rel, -1)
    for rel in [128, -132, 0x12345678, -0x80000000, 0x7FFFFFFF, 4096]:
        add("(e/jmp-rel32 $ %d)" % rel, "jmp {L}+5%+d" % rel, -4)
    for name in ["ret", "leave", "ud2", "int3", "cld", "mfence", "lfence", "sfence", "pause"]:
        add("(e/%s $)" % name, name)
    for length in range(1, 10):
        add("(e/nop $ %d)" % length, ".nops %d" % length)
    for bits, suffix in [(8, "b"), (16, "w"), (32, "d"), (64, "q")]:
        add("(e/rep-movs $ %d)" % bits, "rep movs%s" % suffix)
        add("(e/rep-stos $ %d)" % bits, "rep stos%s" % suffix)

    # --- atomics ---------------------------------------------------------
    for name in ["cmpxchg", "xadd"]:
        for bits in BITS:
            for d, s in [(1, 2), (6, 7), (12, 0), (5, 13)]:
                add("(e/%s-rr $ %d %d %d)" % (name, bits, d, s),
                    "%s %s, %s" % (name, reg(bits, d), reg(bits, s)))
            for i, m in enumerate(SMALL):
                r = [1, 6, 4, 9, 7, 13][i]
                add("(e/%s-mr $ %d %s %d)" % (name, bits, m.coil(), r),
                    "%s %s, %s" % (name, m.asm(bits), reg(bits, r)), m.field)
                add("(e/lock-%s-mr $ %d %s %d)" % (name, bits, m.coil(), r),
                    "lock %s %s, %s" % (name, m.asm(bits), reg(bits, r)), m.field)
    for op, name in enumerate(alu[:7]):
        const = "e/" + name.upper()
        for i, m in enumerate(SMALL):
            bits = BITS[(i + op) % 4]
            r = [1, 6, 4, 9, 7, 13][i]
            add("(e/lock-alu-mr $ %s %d %s %d)" % (const, bits, m.coil(), r),
                "lock %s %s, %s" % (name, m.asm(bits), reg(bits, r)), m.field)
            for v in [1, 0x1234]:
                width = bits if (v == 1 or bits != 8) else 32
                add("(e/lock-alu-mi $ %s %d %s %d)" % (const, width, m.coil(), v),
                    "lock %s %s, %d" % (name, m.asm(width), v), m.field)
    for name in ["inc", "dec", "neg", "not"]:
        for i, m in enumerate(SMALL):
            for bits in BITS:
                add("(e/lock-unary-m $ e/%s %d %s)" % (name.upper(), bits, m.coil()),
                    "lock %s %s" % (name, m.asm(bits)), m.field)

    # --- SSE -------------------------------------------------------------
    xpairs = [(0, 1), (1, 0), (8, 15), (7, 9), (13, 5)]
    xmems = [(0, M(0)), (9, M(4, 8)), (5, M(5)), (15, M(13, 0x100, 1, 4)),
             (1, M(12, -8, 15, 8)), (12, M("rip", RIP_DISP))]

    for name, width in [("movss", 32), ("movsd", 64), ("movaps", 128), ("movapd", 128),
                        ("movups", 128), ("movupd", 128), ("movdqa", 128), ("movdqu", 128)]:
        const = "e/" + name.upper()
        for d, s in xpairs:
            add("(e/sse-mov-rr $ %s %d %d)" % (const, 32 + d, 32 + s),
                "%s %s, %s" % (name, xmm(d), xmm(s)))
        for x, m in xmems:
            add("(e/sse-mov-rm $ %s %d %s)" % (const, 32 + x, m.coil()),
                "%s %s, %s" % (name, xmm(x), m.asm(width)), m.field)
            add("(e/sse-mov-mr $ %s %s %d)" % (const, m.coil(), 32 + x),
                "%s %s, %s" % (name, m.asm(width), xmm(x)), m.field)

    generic = [
        ("addss", 32), ("addsd", 64), ("subss", 32), ("subsd", 64), ("mulss", 32),
        ("mulsd", 64), ("divss", 32), ("divsd", 64), ("sqrtss", 32), ("sqrtsd", 64),
        ("minss", 32), ("minsd", 64), ("maxss", 32), ("maxsd", 64),
        ("ucomiss", 32), ("ucomisd", 64), ("comiss", 32), ("comisd", 64),
        ("cvtss2sd", 32), ("cvtsd2ss", 64), ("cvtps2pd", 64), ("cvtpd2ps", 128),
        ("cvtdq2ps", 128), ("cvtps2dq", 128), ("cvttps2dq", 128), ("cvtdq2pd", 64),
        ("cvttpd2dq", 128),
        ("addps", 128), ("addpd", 128), ("subps", 128), ("subpd", 128), ("mulps", 128),
        ("mulpd", 128), ("divps", 128), ("divpd", 128), ("minps", 128), ("minpd", 128),
        ("maxps", 128), ("maxpd", 128), ("sqrtps", 128), ("sqrtpd", 128),
        ("andps", 128), ("andpd", 128), ("andnps", 128), ("andnpd", 128), ("orps", 128),
        ("orpd", 128), ("xorps", 128), ("xorpd", 128), ("pand", 128), ("pandn", 128),
        ("por", 128), ("pxor", 128),
        ("paddb", 128), ("paddw", 128), ("paddd", 128), ("paddq", 128), ("psubb", 128),
        ("psubw", 128), ("psubd", 128), ("psubq", 128), ("pmullw", 128), ("pmuludq", 128),
        ("pcmpeqb", 128), ("pcmpeqw", 128), ("pcmpeqd", 128), ("pcmpgtb", 128),
        ("pcmpgtw", 128), ("pcmpgtd", 128), ("pminub", 128), ("pmaxub", 128),
        ("pminsw", 128), ("pmaxsw", 128),
        ("psllw", 128), ("pslld", 128), ("psllq", 128), ("psrlw", 128), ("psrld", 128),
        ("psrlq", 128), ("psraw", 128), ("psrad", 128),
        ("punpcklbw", 128), ("punpcklwd", 128), ("punpckldq", 128), ("punpcklqdq", 128),
        ("punpckhbw", 128), ("punpckhwd", 128), ("punpckhdq", 128), ("punpckhqdq", 128),
        ("packsswb", 128), ("packuswb", 128), ("packssdw", 128),
        ("unpcklps", 128), ("unpcklpd", 128), ("unpckhps", 128), ("unpckhpd", 128),
        ("movq", 64),
        ("pshufb", 128), ("pmulld", 128), ("pcmpeqq", 128), ("ptest", 128),
    ]
    for n, (name, width) in enumerate(generic):
        const = "e/" + name.upper()
        for d, s in [xpairs[n % 5], xpairs[(n + 2) % 5], xpairs[(n + 3) % 5]]:
            add("(e/sse-rr $ %s %d %d)" % (const, 32 + d, 32 + s),
                "%s %s, %s" % (name, xmm(d), xmm(s)))
        for x, m in [xmems[n % 6], xmems[(n + 1) % 6], xmems[(n + 3) % 6]]:
            add("(e/sse-rm $ %s %d %s)" % (const, 32 + x, m.coil()),
                "%s %s, %s" % (name, xmm(x), m.asm(width)), m.field)

    with_imm = [("pshufd", 128), ("pshuflw", 128), ("pshufhw", 128), ("shufps", 128),
                ("shufpd", 128), ("cmpps", 128), ("cmppd", 128), ("cmpss", 32),
                ("cmpsd", 64), ("roundps", 128), ("roundpd", 128), ("roundss", 32),
                ("roundsd", 64)]
    for n, (name, width) in enumerate(with_imm):
        const = "e/" + name.upper()
        imms = [0, 1, 2, 3] if name == "shufpd" else [0, 1, 4, 7] if name.startswith("cmp") \
            else [0, 3, 8, 11] if name.startswith("round") else [0, 0x1B, 0x80, 0xFF]
        for i, (d, s) in enumerate([xpairs[n % 5], xpairs[(n + 2) % 5], xpairs[(n + 3) % 5]]):
            add("(e/sse-rri $ %s %d %d %d)" % (const, 32 + d, 32 + s, imms[i]),
                "%s %s, %s, %d" % (name, xmm(d), xmm(s), imms[i]))
        for i, (x, m) in enumerate(xmems):
            add("(e/sse-rmi $ %s %d %s %d)" % (const, 32 + x, m.coil(), imms[i % 4]),
                "%s %s, %s, %d" % (name, xmm(x), m.asm(width), imms[i % 4]), m.field)

    for name in ["psllw", "pslld", "psllq", "psrlw", "psrld", "psrlq", "psraw", "psrad",
                 "pslldq", "psrldq"]:
        for x, count in [(0, 1), (1, 5), (9, 15), (15, 0)]:
            add("(e/sse-shift-ri $ e/%s-I %d %d)" % (name.upper(), 32 + x, count),
                "%s %s, %d" % (name, xmm(x), count))
    for name in ["pmovmskb", "movmskps", "movmskpd"]:
        for d, s in [(0, 1), (1, 0), (9, 12), (4, 15), (13, 5)]:
            add("(e/sse-rx $ e/%s %d %d)" % (name.upper(), d, 32 + s),
                "%s %s, %s" % (name, reg(32, d), xmm(s)))

    for bits, name in [(32, "movd"), (64, "movq")]:
        for x, r in [(0, 0), (1, 5), (9, 12), (15, 4), (5, 13)]:
            add("(e/movd-xr $ %d %d %d)" % (bits, 32 + x, r),
                "%s %s, %s" % (name, xmm(x), reg(bits, r)))
            add("(e/movd-rx $ %d %d %d)" % (bits, r, 32 + x),
                "%s %s, %s" % (name, reg(bits, r), xmm(x)))
        for x, m in xmems:
            add("(e/movd-xm $ %d %d %s)" % (bits, 32 + x, m.coil()),
                "%s %s, %s" % (name, xmm(x), m.asm(bits)), m.field)
            add("(e/movd-mx $ %d %s %d)" % (bits, m.coil(), 32 + x),
                "%s %s, %s" % (name, m.asm(bits), xmm(x)), m.field)

    for fp, suffix in [(32, "ss"), (64, "sd")]:
        for bits in [32, 64]:
            for x, r in [(0, 0), (1, 5), (9, 12), (15, 4), (5, 13)]:
                add("(e/cvtsi2fp-rr $ %d %d %d %d)" % (fp, bits, 32 + x, r),
                    "cvtsi2%s %s, %s" % (suffix, xmm(x), reg(bits, r)))
                add("(e/cvttfp2si-rr $ %d %d %d %d)" % (fp, bits, r, 32 + x),
                    "cvtt%s2si %s, %s" % (suffix, reg(bits, r), xmm(x)))
            for x, m in xmems:
                add("(e/cvtsi2fp-rm $ %d %d %d %s)" % (fp, bits, 32 + x, m.coil()),
                    "cvtsi2%s %s, %s" % (suffix, xmm(x), m.asm(bits)), m.field)
                add("(e/cvttfp2si-rm $ %d %d %d %s)" % (fp, bits, x, m.coil()),
                    "cvtt%s2si %s, %s" % (suffix, reg(bits, x), m.asm(fp)), m.field)

    for bits, suffix in [(8, "b"), (16, "w"), (32, "d"), (64, "q")]:
        lanes = 128 // bits
        gpr_bits = 64 if bits == 64 else 32
        for x, r, lane in [(0, 0, 0), (1, 5, lanes - 1), (9, 12, 1), (15, 4, 0), (5, 13, 1)]:
            add("(e/pextr-rx $ %d %d %d %d)" % (bits, r, 32 + x, lane),
                "pextr%s %s, %s, %d" % (suffix, reg(gpr_bits, r), xmm(x), lane))
            add("(e/pinsr-xr $ %d %d %d %d)" % (bits, 32 + x, r, lane),
                "pinsr%s %s, %s, %d" % (suffix, xmm(x), reg(gpr_bits, r), lane))
        for i, (x, m) in enumerate(xmems):
            lane = i % lanes
            add("(e/pextr-mx $ %d %s %d %d)" % (bits, m.coil(), 32 + x, lane),
                "pextr%s %s, %s, %d" % (suffix, m.asm(bits), xmm(x), lane), m.field)
            add("(e/pinsr-xm $ %d %d %s %d)" % (bits, 32 + x, m.coil(), lane),
                "pinsr%s %s, %s, %d" % (suffix, xmm(x), m.asm(bits), lane), m.field)

    return out


def rejections():
    rip = "(e/mem-rip 0)"
    ok = "(e/mem 0 0)"
    return [
        # registers
        "(e/mov-rr $ 64 16 0)", "(e/mov-rr $ 64 0 -1)", "(e/mov-rr $ 64 32 0)",
        "(e/mov-rm $ 64 16 %s)" % ok, "(e/mov-mr $ 8 %s 40)" % ok,
        "(e/mov-ri $ 64 16 0)", "(e/movabs-ri $ -1 0)", "(e/zero-r $ 16)",
        "(e/push-r $ 16)", "(e/pop-r $ -1)", "(e/call-r $ 32)", "(e/jmp-r $ 16)",
        "(e/bswap $ 64 16)", "(e/setcc-r $ e/CC-E 16)", "(e/xchg-rr $ 64 0 16)",
        "(e/sse-rr $ e/ADDSD 0 33)", "(e/sse-rr $ e/ADDSD 32 1)", "(e/sse-rr $ e/ADDSD 48 32)",
        "(e/sse-rm $ e/ADDSD 15 %s)" % ok, "(e/sse-mov-rr $ e/MOVAPS 31 32)",
        "(e/sse-mov-mr $ e/MOVAPS %s 0)" % ok, "(e/movd-xr $ 64 0 0)",
        "(e/movd-xr $ 64 32 32)", "(e/movd-rx $ 32 32 32)", "(e/sse-rx $ e/PMOVMSKB 32 32)",
        "(e/cvtsi2fp-rr $ 64 64 32 32)", "(e/cvttfp2si-rr $ 64 64 32 32)",
        "(e/cvttfp2si-rm $ 64 64 32 %s)" % ok, "(e/pextr-rx $ 32 32 32 0)",
        "(e/pinsr-xr $ 32 32 32 0)", "(e/sse-shift-ri $ e/PSLLW-I 1 1)",
        # widths
        "(e/mov-rr $ 0 0 1)", "(e/mov-rr $ 24 0 1)", "(e/mov-rr $ 128 0 1)",
        "(e/mov-rr $ 48 0 1)", "(e/mov-ri $ 12 0 1)", "(e/mov-mi $ 4 %s 1)" % ok,
        "(e/lea $ 16 0 %s)" % ok, "(e/lea $ 8 0 %s)" % ok, "(e/bswap $ 16 0)",
        "(e/imul-rr $ 8 0 1)", "(e/imul-rri $ 8 0 1 2)", "(e/cmov-rr $ e/CC-E 8 0 1)",
        "(e/scan-rr $ e/BSF 8 0 1)", "(e/bt-ri $ e/BT 8 0 1)", "(e/bt-rr $ e/BT 8 0 1)",
        "(e/shld-rri $ 8 0 1 1)", "(e/shld-rrc $ 8 0 1)", "(e/sign-extend-rax-rdx $ 8)",
        "(e/movzx-rr $ 8 8 0 1)", "(e/movzx-rr $ 16 16 0 1)", "(e/movzx-rr $ 32 32 0 1)",
        "(e/movzx-rr $ 16 32 0 1)", "(e/movsx-rr $ 32 32 0 1)", "(e/movsx-rr $ 64 64 0 1)",
        "(e/movsx-rm $ 16 16 0 %s)" % ok, "(e/movzx-rm $ 64 64 0 %s)" % ok,
        "(e/rep-movs $ 24)", "(e/rep-stos $ 0)", "(e/movd-xr $ 16 32 0)",
        "(e/movd-xm $ 8 32 %s)" % ok, "(e/cvtsi2fp-rr $ 16 32 32 0)",
        "(e/cvtsi2fp-rr $ 32 16 32 0)", "(e/cvttfp2si-rr $ 32 8 0 32)",
        # memory operands
        "(e/mov-rm $ 64 0 (e/mem 0 2147483648))", "(e/mov-rm $ 64 0 (e/mem 0 -2147483649))",
        "(e/mov-rm $ 64 0 (e/mem 16 0))", "(e/mov-rm $ 64 0 (e/mem -3 0))",
        "(e/mov-rm $ 64 0 (e/mem 32 0))",
        "(e/mov-rm $ 64 0 (e/mem-index 0 4 1 0))", "(e/mov-rm $ 64 0 (e/mem-index 0 16 1 0))",
        "(e/mov-rm $ 64 0 (e/mem-index 0 1 3 0))", "(e/mov-rm $ 64 0 (e/mem-index 0 1 0 0))",
        "(e/mov-rm $ 64 0 (e/mem-index 0 1 16 0))", "(e/mov-rm $ 64 0 (e/mem-index -2 1 1 0))",
        "(e/mov-rm $ 64 0 (e/mem-index 0 -2 1 0))", "(e/mov-rm $ 64 0 (e/mem-rip 2147483648))",
        "(e/lea $ 64 0 (e/mem-index -1 4 8 0))", "(e/push-m $ (e/mem 0 4294967296))",
        "(e/call-m $ (e/mem-index 1 4 2 0))", "(e/jmp-m $ (e/mem 99 0))",
        "(e/sse-rm $ e/ADDSD 32 (e/mem-index 0 4 1 0))",
        "(e/sse-mov-mr $ e/MOVSD (e/mem 0 2147483648) 32)",
        "(e/alu-mi $ e/ADD 32 (e/mem-index 0 4 1 0) 1)",
        "(e/pinsr-xm $ 16 32 (e/mem 16 0) 0)", "(e/pextr-mx $ 16 (e/mem 16 0) 32 0)",
        # immediates
        "(e/mov-ri $ 8 0 256)", "(e/mov-ri $ 8 0 -129)", "(e/mov-ri $ 16 0 65536)",
        "(e/mov-ri $ 32 0 4294967296)", "(e/mov-ri $ 32 0 -2147483649)",
        "(e/mov-mi $ 64 %s 2147483648)" % ok, "(e/mov-mi $ 8 %s 256)" % ok,
        "(e/alu-ri $ e/ADD 64 0 2147483648)", "(e/alu-ri $ e/ADD 64 0 4294967295)",
        "(e/alu-ri $ e/ADD 8 0 256)", "(e/alu-ri $ e/CMP 32 1 4294967296)",
        "(e/alu-mi $ e/ADD 64 %s 2147483648)" % ok, "(e/alu-mi $ e/ADD 16 %s 65536)" % ok,
        "(e/test-ri $ 64 1 2147483648)", "(e/test-ri $ 8 1 256)",
        "(e/test-mi $ 64 %s 2147483648)" % ok, "(e/imul-rri $ 64 0 1 2147483648)",
        "(e/imul-rmi $ 16 0 %s 65536)" % ok, "(e/push-i $ 2147483648)",
        "(e/push-i $ -2147483649)",
        "(e/sse-rri $ e/PSHUFD 32 33 256)", "(e/sse-rri $ e/PSHUFD 32 33 -1)",
        "(e/sse-rmi $ e/PSHUFD 32 %s 256)" % ok, "(e/sse-shift-ri $ e/PSLLW-I 32 256)",
        # displacements of branches
        "(e/jmp-rel8 $ 128)", "(e/jmp-rel8 $ -129)", "(e/jcc-rel8 $ e/CC-E 128)",
        "(e/jcc-rel8 $ e/CC-E -129)", "(e/jmp-rel32 $ 2147483648)",
        "(e/jcc-rel32 $ e/CC-E -2147483649)", "(e/call-rel32 $ 2147483648)",
        # operation selectors
        "(e/alu-rr $ 8 64 0 1)", "(e/alu-rr $ -1 64 0 1)", "(e/alu-rm $ 8 64 0 %s)" % ok,
        "(e/alu-mr $ 8 64 %s 0)" % ok, "(e/alu-ri $ 8 64 0 1)", "(e/alu-mi $ 8 64 %s 1)" % ok,
        "(e/unary-r $ 0 64 0)", "(e/unary-r $ 1 64 0)", "(e/unary-r $ 10 64 0)",
        "(e/unary-m $ 10 64 %s)" % ok, "(e/shift-ri $ 6 64 0 1)", "(e/shift-ri $ 8 64 0 1)",
        "(e/shift-rc $ 6 64 0)", "(e/shift-mi $ 6 64 %s 1)" % ok, "(e/shift-mc $ -1 64 %s)" % ok,
        "(e/bt-ri $ 4 64 0 1)", "(e/bt-rr $ -1 64 0 1)", "(e/bt-mi $ 4 64 %s 1)" % ok,
        "(e/bt-mr $ 4 64 %s 1)" % ok, "(e/scan-rr $ 0 64 0 1)",
        "(e/scan-rr $ e/ADDSD 64 0 1)", "(e/scan-rm $ 7 64 0 %s)" % ok,
        "(e/setcc-r $ 16 0)", "(e/setcc-r $ -1 0)", "(e/setcc-m $ 16 %s)" % ok,
        "(e/cmov-rr $ 16 64 0 1)", "(e/cmov-rm $ 16 64 0 %s)" % ok,
        "(e/jcc-rel8 $ 16 0)", "(e/jcc-rel32 $ -1 0)",
        "(e/lock-alu-mr $ e/CMP 64 %s 0)" % ok, "(e/lock-alu-mi $ e/CMP 64 %s 0)" % ok,
        "(e/lock-alu-mr $ 8 64 %s 0)" % ok, "(e/lock-unary-m $ e/MUL 64 %s)" % ok,
        "(e/lock-unary-m $ e/IDIV 64 %s)" % ok,
        # shift counts, bit indexes, lanes, nop lengths
        "(e/shift-ri $ e/SHL 64 0 64)", "(e/shift-ri $ e/SHL 32 0 32)",
        "(e/shift-ri $ e/SHL 8 0 8)", "(e/shift-ri $ e/SHL 64 0 -1)",
        "(e/shift-mi $ e/SAR 16 %s 16)" % ok, "(e/shld-rri $ 32 0 1 32)",
        "(e/shrd-rri $ 64 0 1 64)", "(e/bt-ri $ e/BT 32 0 32)", "(e/bt-mi $ e/BTS 64 %s 64)" % ok,
        "(e/pextr-rx $ 8 0 32 16)", "(e/pextr-rx $ 16 0 32 8)", "(e/pextr-rx $ 32 0 32 4)",
        "(e/pextr-rx $ 64 0 32 2)", "(e/pextr-rx $ 64 0 32 -1)", "(e/pinsr-xr $ 64 32 0 2)",
        "(e/pinsr-xm $ 8 32 %s 16)" % ok, "(e/pextr-mx $ 32 %s 32 4)" % ok,
        "(e/pextr-rx $ 24 0 32 0)", "(e/nop $ 0)", "(e/nop $ 10)", "(e/nop $ -1)",
        # SSE operand forms
        "(e/sse-rr $ e/PSHUFD 32 33)", "(e/sse-rr $ e/PSLLW-I 32 33)",
        "(e/sse-rr $ e/PMOVMSKB 32 33)", "(e/sse-rr $ e/MOVAPS 32 33)",
        "(e/sse-rm $ e/PSHUFD 32 %s)" % ok, "(e/sse-rm $ e/MOVSD 32 %s)" % ok,
        "(e/sse-rri $ e/ADDSD 32 33 0)", "(e/sse-rmi $ e/ADDSD 32 %s 0)" % ok,
        "(e/sse-shift-ri $ e/PSLLW 32 1)", "(e/sse-rx $ e/ADDPS 0 32)",
        "(e/sse-mov-rr $ e/ADDSD 32 33)", "(e/sse-mov-rm $ e/MOVQ 32 %s)" % ok,
        "(e/sse-mov-mr $ e/PXOR %s 32)" % ok,
        "(e/mov-rm $ 64 0 (e/mem-index -2 0 1 0))",
    ] + ["(e/mov-rm $ 64 0 (e/Mem :base e/RIP :index 1 :scale 1 :disp 0))",
         "(e/lea $ 64 0 (e/Mem :base 0 :index 4 :scale 2 :disp 0))",
         "(e/alu-rm $ e/ADD 64 0 %s)" % rip.replace("0)", "4294967296)")]


EXTRA = """
(defn expect [(condition bool) (what (slice u8))] (-> i64)
  (if condition
      0
      (do
        (println "extra check failed: {}" what)
        1)))

(defn field-end [(b (mut (ArrayList u8))) (result (Result i64 (slice u8)))
                 (expected i64)] (-> i64)
  (let [distance (match result (Ok [field] (e/field-to-end b field)) (Err [_] -1))]
    (clear! (mut b))
    (expect (= distance expected) "distance from a patchable field to the instruction end")))

;;; Checks that are not byte comparisons: the condition table, and the distance
;;; from a patchable field to the end of its instruction, which is what a
;;; PC-relative relocation's addend must cancel.
(defn extra-checks [(b (mut (ArrayList u8)))] (-> i64)
  (+ (expect (= (e/invert e/CC-O) e/CC-NO) "invert o")
     (expect (= (e/invert e/CC-NO) e/CC-O) "invert no")
     (expect (= (e/invert e/CC-B) e/CC-AE) "invert b")
     (expect (= (e/invert e/CC-AE) e/CC-B) "invert ae")
     (expect (= (e/invert e/CC-E) e/CC-NE) "invert e")
     (expect (= (e/invert e/CC-NE) e/CC-E) "invert ne")
     (expect (= (e/invert e/CC-BE) e/CC-A) "invert be")
     (expect (= (e/invert e/CC-A) e/CC-BE) "invert a")
     (expect (= (e/invert e/CC-S) e/CC-NS) "invert s")
     (expect (= (e/invert e/CC-NS) e/CC-S) "invert ns")
     (expect (= (e/invert e/CC-P) e/CC-NP) "invert p")
     (expect (= (e/invert e/CC-NP) e/CC-P) "invert np")
     (expect (= (e/invert e/CC-L) e/CC-GE) "invert l")
     (expect (= (e/invert e/CC-GE) e/CC-L) "invert ge")
     (expect (= (e/invert e/CC-LE) e/CC-G) "invert le")
     (expect (= (e/invert e/CC-G) e/CC-LE) "invert g")
     (expect (and (= e/CC-O 0) (= e/CC-B 2) (= e/CC-E 4) (= e/CC-BE 6) (= e/CC-S 8)
                  (= e/CC-P 10) (= e/CC-L 12) (= e/CC-LE 14))
             "condition numbering")
     (expect (and (e/condition? 0) (e/condition? 15) (not (e/condition? 16))
                  (not (e/condition? -1)))
             "condition range")
     (expect (and (= (e/sse-feature e/ADDSD) e/FEATURE-SSE2)
                  (= (e/sse-feature e/PSHUFD) e/FEATURE-SSE2)
                  (= (e/sse-feature e/PSLLW-I) e/FEATURE-SSE2)
                  (= (e/sse-feature e/PMOVMSKB) e/FEATURE-SSE2)
                  (= (e/sse-feature e/MOVDQA) e/FEATURE-SSE2)
                  (= (e/sse-feature e/PSHUFB) e/FEATURE-SSSE3)
                  (= (e/sse-feature e/PMULLD) e/FEATURE-SSE41)
                  (= (e/sse-feature e/PCMPEQQ) e/FEATURE-SSE41)
                  (= (e/sse-feature e/PTEST) e/FEATURE-SSE41)
                  (= (e/sse-feature e/ROUNDSS) e/FEATURE-SSE41)
                  (= (e/sse-feature e/ROUNDSD) e/FEATURE-SSE41))
             "SSE feature levels")
     (field-end (mut b) (e/mov-rm (mut b) 64 0 (e/mem-rip 0)) 4)
     (field-end (mut b) (e/lea (mut b) 64 9 (e/mem-rip 0)) 4)
     (field-end (mut b) (e/sse-rm (mut b) e/ADDSD 32 (e/mem-rip 0)) 4)
     (field-end (mut b) (e/alu-mi (mut b) e/CMP 64 (e/mem-rip 0) 5) 5)
     (field-end (mut b) (e/alu-mi (mut b) e/CMP 8 (e/mem-rip 0) 5) 5)
     (field-end (mut b) (e/alu-mi (mut b) e/CMP 16 (e/mem-rip 0) 4660) 6)
     (field-end (mut b) (e/alu-mi (mut b) e/CMP 32 (e/mem-rip 0) 305419896) 8)
     (field-end (mut b) (e/mov-mi (mut b) 8 (e/mem-rip 0) 1) 5)
     (field-end (mut b) (e/mov-mi (mut b) 16 (e/mem-rip 0) 1) 6)
     (field-end (mut b) (e/mov-mi (mut b) 32 (e/mem-rip 0) 1) 8)
     (field-end (mut b) (e/mov-mi (mut b) 64 (e/mem-rip 0) 1) 8)
     (field-end (mut b) (e/test-mi (mut b) 32 (e/mem-rip 0) 1) 8)
     (field-end (mut b) (e/shift-mi (mut b) e/SHL 64 (e/mem-rip 0) 3) 5)
     (field-end (mut b) (e/shift-mi (mut b) e/SHL 64 (e/mem-rip 0) 1) 4)
     (field-end (mut b) (e/imul-rmi (mut b) 64 0 (e/mem-rip 0) 1000) 8)
     (field-end (mut b) (e/sse-rmi (mut b) e/PSHUFD 32 (e/mem-rip 0) 27) 5)
     (field-end (mut b) (e/pinsr-xm (mut b) 32 32 (e/mem-rip 0) 1) 5)
     (field-end (mut b) (e/call-rel32 (mut b) 0) 4)
     (field-end (mut b) (e/jmp-rel32 (mut b) 0) 4)
     (field-end (mut b) (e/jcc-rel32 (mut b) e/CC-NE 0) 4)
     (field-end (mut b) (e/jmp-rel8 (mut b) 0) 1)
     (field-end (mut b) (e/jcc-rel8 (mut b) e/CC-NE 0) 1)
     (field-end (mut b) (e/movabs-ri (mut b) 0 0) 8)
     (field-end (mut b) (e/mov-ri (mut b) 64 0 81985529216486895) 8)))
"""
