
/tmp/coil-stogir-static-views.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_static_views>:
       0:      	mov	x16, #0x40              ; =64
       4:      	movk	x16, #0x1, lsl #16
       8:      	sub	sp, sp, x16
       c:      	str	x29, [sp]
      10:      	str	x30, [sp, #0x8]
      14:      	mov	x29, sp
      18:      	mov	x16, #0x30              ; =48
      1c:      	movk	x16, #0x1, lsl #16
      20:      	add	x16, sp, x16
      24:      	str	x19, [x16]
      28:      	add	x16, x29, #0x10
      2c:      	mov	x17, #0xffff            ; =65535
      30:      	add	x2, x16, x17
      34:      	sub	sp, sp, #0x20
      38:      	mov	x3, sp
      3c:      	mov	w17, #0x5a              ; =90
      40:      	strb	w17, [x2]
      44:      	mov	x16, #0x10              ; =16
      48:      	movk	x16, #0x1, lsl #16
      4c:      	add	x16, x29, x16, uxtx
      50:      	adrp	x17, 0x0 <_static_views>
		0000000000000050:  ARM64_RELOC_PAGE21	L_stogir_0000000000000000
      54:      	add	x17, x17, #0x0
		0000000000000054:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000000
      58:      	ldr	q31, [x17]
      5c:      	stur	q31, [x16, #0x1]
      60:      	mov	x30, x1
      64:      	mov	x1, #0x10               ; =16
      68:      	movk	x1, #0x1, lsl #16
      6c:      	add	x1, x29, x1, uxtx
      70:      	add	x4, x29, #0x10
      74:      	mov	x19, x0
      78:      	mov	x2, #0x1                ; =1
      7c:      	mov	x3, #0x10               ; =16
      80:      	mov	x5, #0x1                ; =1
      84:      	mov	x6, #0xa7               ; =167
      88:      	blr	x30
      8c:      	mov	x16, #0x10              ; =16
      90:      	movk	x16, #0x1, lsl #16
      94:      	add	x16, x29, x16, uxtx
      98:      	ldur	q0, [x16, #0x1]
      9c:      	str	q0, [x19, #0x10]
      a0:      	sub	sp, x29, #0x0
      a4:      	mov	x16, #0x30              ; =48
      a8:      	movk	x16, #0x1, lsl #16
      ac:      	add	x16, sp, x16
      b0:      	ldr	x19, [x16]
      b4:      	ldr	x29, [sp]
      b8:      	ldr	x30, [sp, #0x8]
      bc:      	mov	x16, #0x40              ; =64
      c0:      	movk	x16, #0x1, lsl #16
      c4:      	add	sp, sp, x16
      c8:      	ret
