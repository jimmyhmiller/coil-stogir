
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/operand-control-gap/build/operand-control/llvm.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <ltmp0>:
       0:      	cbz	x2, 0x20 <ltmp0+0x20>
       4:      	stp	x29, x30, [sp, #-0x10]!
       8:      	mov	x29, sp
       c:      	bl	0xc <ltmp0+0xc>
		000000000000000c:  ARM64_RELOC_BRANCH26	_memcmp
      10:      	cmp	w0, #0x0
      14:      	cset	w0, eq
      18:      	ldp	x29, x30, [sp], #0x10
      1c:      	ret
      20:      	mov	w0, #0x1                ; =1
      24:      	ret

0000000000000028 <_coil.hashmap.bytewise-hash>:
      28:      	mov	x8, x0
      2c:      	mov	x0, #0x2325             ; =8997
      30:      	cmp	x1, #0x1
      34:      	movk	x0, #0x8422, lsl #16
      38:      	movk	x0, #0x9ce4, lsl #32
      3c:      	movk	x0, #0xcbf2, lsl #48
      40:      	b.lt	0x60 <_coil.hashmap.bytewise-hash+0x38>
      44:      	mov	x9, #0x1b3              ; =435
      48:      	movk	x9, #0x100, lsl #32
      4c:      	ldrsb	x10, [x8], #0x1
      50:      	subs	x1, x1, #0x1
      54:      	eor	x10, x0, x10
      58:      	mul	x0, x10, x9
      5c:      	b.ne	0x4c <_coil.hashmap.bytewise-hash+0x24>
      60:      	ret

0000000000000064 <_gap_operand_control>:
      64:      	cmp	w1, #0x1
      68:      	b.lt	0xa0 <_gap_operand_control+0x3c>
      6c:      	ldr	x9, [x0, #0x8]
      70:      	mov	w8, w1
      74:      	cmp	x9, x8
      78:      	b.le	0xa0 <_gap_operand_control+0x3c>
      7c:      	ldr	x9, [x0, #0x80]
      80:      	cmp	x9, x8
      84:      	b.le	0xa0 <_gap_operand_control+0x3c>
      88:      	ldr	x9, [x0, #0x78]
      8c:      	ldr	w8, [x9, x8, lsl #2]
      90:      	cmp	w2, w8
      94:      	ccmp	w2, #0x1, #0x8, ls
      98:      	ccmp	w8, #0x0, #0x8, ge
      9c:      	b.pl	0xb8 <_gap_operand_control+0x54>
      a0:      	mov	x8, xzr
      a4:      	sxtw	x9, w9
      a8:      	cmp	w8, #0x1
      ac:      	mov	x8, #-0x8000000000000000 ; =-9223372036854775808
      b0:      	csel	x0, x9, x8, eq
      b4:      	ret
      b8:      	add	w8, w1, w2, lsr #2
      bc:      	ldr	x9, [x0]
      c0:      	add	x8, x9, w8, uxtw #4
      c4:      	and	w9, w2, #0x3
      c8:      	ldr	w9, [x8, w9, uxtw #2]
      cc:      	mov	w8, #0x1                ; =1
      d0:      	sxtw	x9, w9
      d4:      	cmp	w8, #0x1
      d8:      	mov	x8, #-0x8000000000000000 ; =-9223372036854775808
      dc:      	csel	x0, x9, x8, eq
      e0:      	ret
