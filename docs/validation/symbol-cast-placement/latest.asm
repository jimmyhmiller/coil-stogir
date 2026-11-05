
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/symbol-cast-placement/build/hot-code-audit/kernel.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_symbol_placement>:
       0:      	sub	sp, sp, #0x20
       4:      	str	x19, [sp]
       8:      	str	x20, [sp, #0x8]
       c:      	str	x21, [sp, #0x10]
      10:      	str	x22, [sp, #0x18]
      14:      	add	x3, x1, #0x0
      18:      	add	x4, x1, #0x1
      1c:      	add	x5, x1, #0x2
      20:      	add	x6, x1, #0x3
      24:      	add	x7, x1, #0x4
      28:      	add	x8, x1, #0x5
      2c:      	add	x9, x1, #0x6
      30:      	add	x10, x1, #0x7
      34:      	add	x11, x1, #0x8
      38:      	add	x12, x1, #0x9
      3c:      	add	x13, x1, #0xa
      40:      	add	x14, x1, #0xb
      44:      	add	x15, x1, #0xc
      48:      	add	x19, x1, #0xd
      4c:      	add	x20, x1, #0xe
      50:      	add	x1, x1, #0xf
      54:      	movz	x21, #0x0, lsl #48
      58:      	b	0x1c4 <_symbol_placement+0x1c4>
      5c:      	nop
      60:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000060:  ARM64_RELOC_PAGE21	L_stogir_0000000000000000
      64:      	add	x16, x16, #0x0
		0000000000000064:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000000
      68:      	orr	x22, x16, xzr
      6c:      	str	x22, [x2]
      70:      	cmp	x21, x5
      74:      	b.ne	0x88 <_symbol_placement+0x88>
      78:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000078:  ARM64_RELOC_PAGE21	L_stogir_0000000000000001
      7c:      	add	x16, x16, #0x0
		000000000000007c:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000001
      80:      	orr	x22, x16, xzr
      84:      	str	x22, [x2]
      88:      	cmp	x21, x6
      8c:      	b.ne	0xa0 <_symbol_placement+0xa0>
      90:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000090:  ARM64_RELOC_PAGE21	L_stogir_0000000000000002
      94:      	add	x16, x16, #0x0
		0000000000000094:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000002
      98:      	orr	x22, x16, xzr
      9c:      	str	x22, [x2]
      a0:      	cmp	x21, x7
      a4:      	b.ne	0xb8 <_symbol_placement+0xb8>
      a8:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000000a8:  ARM64_RELOC_PAGE21	L_stogir_0000000000000003
      ac:      	add	x16, x16, #0x0
		00000000000000ac:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000003
      b0:      	orr	x22, x16, xzr
      b4:      	str	x22, [x2]
      b8:      	cmp	x21, x8
      bc:      	b.ne	0xd0 <_symbol_placement+0xd0>
      c0:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000000c0:  ARM64_RELOC_PAGE21	L_stogir_0000000000000004
      c4:      	add	x16, x16, #0x0
		00000000000000c4:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000004
      c8:      	orr	x22, x16, xzr
      cc:      	str	x22, [x2]
      d0:      	cmp	x21, x9
      d4:      	b.ne	0xe8 <_symbol_placement+0xe8>
      d8:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000000d8:  ARM64_RELOC_PAGE21	L_stogir_0000000000000005
      dc:      	add	x16, x16, #0x0
		00000000000000dc:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000005
      e0:      	orr	x22, x16, xzr
      e4:      	str	x22, [x2]
      e8:      	cmp	x21, x10
      ec:      	b.ne	0x100 <_symbol_placement+0x100>
      f0:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000000f0:  ARM64_RELOC_PAGE21	L_stogir_0000000000000006
      f4:      	add	x16, x16, #0x0
		00000000000000f4:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000006
      f8:      	orr	x22, x16, xzr
      fc:      	str	x22, [x2]
     100:      	cmp	x21, x11
     104:      	b.ne	0x118 <_symbol_placement+0x118>
     108:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000108:  ARM64_RELOC_PAGE21	L_stogir_0000000000000007
     10c:      	add	x16, x16, #0x0
		000000000000010c:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000007
     110:      	orr	x22, x16, xzr
     114:      	str	x22, [x2]
     118:      	cmp	x21, x12
     11c:      	b.ne	0x130 <_symbol_placement+0x130>
     120:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000120:  ARM64_RELOC_PAGE21	L_stogir_0000000000000008
     124:      	add	x16, x16, #0x0
		0000000000000124:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000008
     128:      	orr	x22, x16, xzr
     12c:      	str	x22, [x2]
     130:      	cmp	x21, x13
     134:      	b.ne	0x148 <_symbol_placement+0x148>
     138:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000138:  ARM64_RELOC_PAGE21	L_stogir_0000000000000009
     13c:      	add	x16, x16, #0x0
		000000000000013c:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000009
     140:      	orr	x22, x16, xzr
     144:      	str	x22, [x2]
     148:      	cmp	x21, x14
     14c:      	b.ne	0x160 <_symbol_placement+0x160>
     150:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000150:  ARM64_RELOC_PAGE21	L_stogir_000000000000000a
     154:      	add	x16, x16, #0x0
		0000000000000154:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000a
     158:      	orr	x22, x16, xzr
     15c:      	str	x22, [x2]
     160:      	cmp	x21, x15
     164:      	b.ne	0x178 <_symbol_placement+0x178>
     168:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000168:  ARM64_RELOC_PAGE21	L_stogir_000000000000000b
     16c:      	add	x16, x16, #0x0
		000000000000016c:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000b
     170:      	orr	x22, x16, xzr
     174:      	str	x22, [x2]
     178:      	cmp	x21, x19
     17c:      	b.ne	0x190 <_symbol_placement+0x190>
     180:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000180:  ARM64_RELOC_PAGE21	L_stogir_000000000000000c
     184:      	add	x16, x16, #0x0
		0000000000000184:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000c
     188:      	orr	x22, x16, xzr
     18c:      	str	x22, [x2]
     190:      	cmp	x21, x20
     194:      	b.ne	0x1a8 <_symbol_placement+0x1a8>
     198:      	adrp	x16, 0x0 <_symbol_placement>
		0000000000000198:  ARM64_RELOC_PAGE21	L_stogir_000000000000000d
     19c:      	add	x16, x16, #0x0
		000000000000019c:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000d
     1a0:      	orr	x22, x16, xzr
     1a4:      	str	x22, [x2]
     1a8:      	cmp	x21, x1
     1ac:      	b.ne	0x1c0 <_symbol_placement+0x1c0>
     1b0:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000001b0:  ARM64_RELOC_PAGE21	L_stogir_000000000000000e
     1b4:      	add	x16, x16, #0x0
		00000000000001b4:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000e
     1b8:      	orr	x22, x16, xzr
     1bc:      	str	x22, [x2]
     1c0:      	add	x21, x21, #0x1
     1c4:      	cmp	x21, x0
     1c8:      	b.hs	0x1f0 <_symbol_placement+0x1f0>
     1cc:      	cmp	x21, x3
     1d0:      	b.ne	0x1e4 <_symbol_placement+0x1e4>
     1d4:      	adrp	x16, 0x0 <_symbol_placement>
		00000000000001d4:  ARM64_RELOC_PAGE21	L_stogir_000000000000000f
     1d8:      	add	x16, x16, #0x0
		00000000000001d8:  ARM64_RELOC_PAGEOFF12	L_stogir_000000000000000f
     1dc:      	orr	x22, x16, xzr
     1e0:      	str	x22, [x2]
     1e4:      	cmp	x21, x4
     1e8:      	b.eq	0x60 <_symbol_placement+0x60>
     1ec:      	b	0x70 <_symbol_placement+0x70>
     1f0:      	mov	x0, x21
     1f4:      	ldr	x19, [sp]
     1f8:      	ldr	x20, [sp, #0x8]
     1fc:      	ldr	x21, [sp, #0x10]
     200:      	ldr	x22, [sp, #0x18]
     204:      	add	sp, sp, #0x20
     208:      	ret
