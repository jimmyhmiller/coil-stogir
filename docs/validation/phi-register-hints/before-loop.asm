
build/phi-register-hints/before-loop.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_stogir_loop_test>:
       0:      	movz	x1, #0x0, lsl #48
       4:      	movz	x2, #0x0, lsl #48
       8:      	b	0x20 <_stogir_loop_test+0x20>
       c:      	nop
      10:      	add	x3, x1, #0x1
      14:      	add	x1, x2, x1
      18:      	mov	x2, x1
      1c:      	mov	x1, x3
      20:      	cmp	x1, x0
      24:      	b.lt	0x10 <_stogir_loop_test+0x10>
      28:      	mov	x0, x2
      2c:      	ret
