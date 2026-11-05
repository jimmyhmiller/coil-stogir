
build/phi-register-hints/after-loop.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_stogir_loop_test>:
       0:      	movz	x1, #0x0, lsl #48
       4:      	movz	x2, #0x0, lsl #48
       8:      	b	0x1c <_stogir_loop_test+0x1c>
       c:      	nop
      10:      	add	x3, x1, #0x1
      14:      	add	x2, x2, x1
      18:      	mov	x1, x3
      1c:      	cmp	x1, x0
      20:      	b.lt	0x10 <_stogir_loop_test+0x10>
      24:      	mov	x0, x2
      28:      	ret
