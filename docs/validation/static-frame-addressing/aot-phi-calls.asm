
/tmp/coil-stogir-static-phi-calls.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_static_phi_calls>:
       0:      	sub	sp, sp, #0x50
       4:      	str	x29, [sp, #0x10]
       8:      	str	x30, [sp, #0x18]
       c:      	add	x29, sp, #0x10
      10:      	str	x19, [sp, #0x40]
      14:      	add	x3, x2, #0xd
      18:      	add	x4, x2, #0x1a
      1c:      	str	x3, [sp, #0x20]
      20:      	str	x4, [sp, #0x30]
      24:      	cmp	x2, #0xd
      28:      	b.ne	0x34 <_static_phi_calls+0x34>
      2c:      	add	x2, sp, #0x20
      30:      	b	0x38 <_static_phi_calls+0x38>
      34:      	add	x2, sp, #0x30
      38:      	mov	x19, x1
      3c:      	mov	x30, x0
      40:      	mov	x0, x2
      44:      	blr	x30
      48:      	mov	x30, x19
      4c:      	add	x16, sp, #0x30
      50:      	str	x16, [sp]
      54:      	add	x1, sp, #0x30
      58:      	add	x2, sp, #0x30
      5c:      	add	x3, sp, #0x30
      60:      	add	x4, sp, #0x20
      64:      	add	x5, sp, #0x30
      68:      	add	x6, sp, #0x20
      6c:      	add	x7, sp, #0x30
      70:      	mov	x19, x0
      74:      	add	x0, sp, #0x20
      78:      	blr	x30
      7c:      	ldr	x1, [sp, #0x30]
      80:      	add	x0, x19, x0
      84:      	add	x0, x0, x1
      88:      	ldr	x19, [sp, #0x40]
      8c:      	ldr	x29, [sp, #0x10]
      90:      	ldr	x30, [sp, #0x18]
      94:      	add	sp, sp, #0x50
      98:      	ret
