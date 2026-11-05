
/tmp/coil-stogir-static-phi-calls-dynamic.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_static_phi_calls>:
       0:      	sub	sp, sp, #0x50
       4:      	str	x29, [sp, #0x10]
       8:      	str	x30, [sp, #0x18]
       c:      	add	x29, sp, #0x10
      10:      	str	x19, [sp, #0x40]
      14:      	str	x20, [sp, #0x48]
      18:      	add	x3, x2, #0xd
      1c:      	add	x4, x2, #0x1a
      20:      	sub	sp, sp, #0x10
      24:      	add	x19, sp, #0x10
      28:      	str	x3, [x29, #0x10]
      2c:      	str	x3, [x19]
      30:      	str	x4, [x29, #0x20]
      34:      	cmp	x2, #0xd
      38:      	b.ne	0x44 <_static_phi_calls+0x44>
      3c:      	add	x2, x29, #0x10
      40:      	b	0x48 <_static_phi_calls+0x48>
      44:      	add	x2, x29, #0x20
      48:      	mov	x20, x1
      4c:      	mov	x30, x0
      50:      	mov	x0, x2
      54:      	blr	x30
      58:      	mov	x30, x20
      5c:      	add	x16, x29, #0x20
      60:      	str	x16, [sp]
      64:      	add	x1, x29, #0x20
      68:      	mov	x2, x19
      6c:      	add	x3, x29, #0x20
      70:      	add	x4, x29, #0x10
      74:      	add	x5, x29, #0x20
      78:      	add	x6, x29, #0x10
      7c:      	add	x7, x29, #0x20
      80:      	mov	x19, x0
      84:      	add	x0, x29, #0x10
      88:      	blr	x30
      8c:      	ldr	x1, [x29, #0x20]
      90:      	add	x0, x19, x0
      94:      	add	x0, x0, x1
      98:      	sub	sp, x29, #0x10
      9c:      	ldr	x19, [sp, #0x40]
      a0:      	ldr	x20, [sp, #0x48]
      a4:      	ldr	x29, [sp, #0x10]
      a8:      	ldr	x30, [sp, #0x18]
      ac:      	add	sp, sp, #0x50
      b0:      	ret
