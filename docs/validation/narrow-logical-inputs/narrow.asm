
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/narrow-logical-inputs/build/bulk-streams/copy416.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_bulk_stream_kernel>:
       0:      	mov	x17, #0x1000000000000   ; =281474976710656
       4:      	cmp	x0, x17
       8:      	cset	w2, lo
       c:      	add	x3, x0, #0x0
      10:      	add	x4, x0, #0x1a0
      14:      	mov	x17, #0x1000000000000   ; =281474976710656
      18:      	cmp	x1, x17
      1c:      	cset	w5, lo
      20:      	add	x6, x1, #0x0
      24:      	add	x7, x1, #0x1a0
      28:      	add	x3, x3, #0x0
      2c:      	add	x4, x4, #0x0
      30:      	and	w5, w5, #0x1
      34:      	uxtb	w5, w5
      38:      	add	x6, x6, #0x0
      3c:      	add	x7, x7, #0x0
      40:      	mov	x17, #0x1000000000000   ; =281474976710656
      44:      	cmp	x3, x17
      48:      	cset	w8, lo
      4c:      	mov	x17, #0x1000000000000   ; =281474976710656
      50:      	cmp	x4, x17
      54:      	cset	w9, ls
      58:      	mov	x17, #0x1000000000000   ; =281474976710656
      5c:      	cmp	x6, x17
      60:      	cset	w10, lo
      64:      	cmp	x4, x6
      68:      	cset	w4, ls
      6c:      	mov	x17, #0x1000000000000   ; =281474976710656
      70:      	cmp	x7, x17
      74:      	cset	w6, ls
      78:      	cmp	x7, x3
      7c:      	cset	w3, ls
      80:      	and	w5, w5, w10
      84:      	uxtb	w5, w5
      88:      	orr	w3, w4, w3
      8c:      	uxtb	w3, w3
      90:      	and	w4, w5, w6
      94:      	uxtb	w4, w4
      98:      	and	w2, w2, w4
      9c:      	uxtb	w2, w2
      a0:      	and	w2, w2, w8
      a4:      	uxtb	w2, w2
      a8:      	and	w2, w2, w9
      ac:      	uxtb	w2, w2
      b0:      	and	w2, w3, w2
      b4:      	uxtb	w2, w2
      b8:      	uxtb	w16, w2
      bc:      	cmp	w16, wzr
      c0:      	b.eq	0x120 <_bulk_stream_kernel+0x120>
      c4:      	mov	x16, #0x34              ; =52
      c8:      	sub	x2, x16, #0x0
      cc:      	movz	x16, #0x0, lsl #48
      d0:      	lsl	x3, x16, #3
      d4:      	lsr	x2, x2, #2
      d8:      	add	x4, x1, x3
      dc:      	add	x3, x0, x3
      e0:      	mov	x5, x3
      e4:      	mov	x3, x2
      e8:      	b	0xf8 <_bulk_stream_kernel+0xf8>
      ec:      	nop
      f0:      	add	x4, x4, #0x20
      f4:      	add	x5, x5, #0x20
      f8:      	sub	x3, x3, #0x1
      fc:      	ldr	q0, [x4]
     100:      	str	q0, [x5]
     104:      	ldr	q0, [x4, #0x10]
     108:      	str	q0, [x5, #0x10]
     10c:      	cmp	x3, #0x0
     110:      	b.ne	0xf0 <_bulk_stream_kernel+0xf0>
     114:      	lsl	x2, x2, #2
     118:      	add	x2, x2, #0x0
     11c:      	b	0x124 <_bulk_stream_kernel+0x124>
     120:      	movz	x2, #0x0, lsl #48
     124:      	b	0x140 <_bulk_stream_kernel+0x140>
     128:      	lsl	x3, x2, #3
     12c:      	add	x2, x2, #0x1
     130:      	add	x4, x0, x3
     134:      	add	x3, x1, x3
     138:      	ldr	x3, [x3]
     13c:      	str	x3, [x4]
     140:      	cmp	x2, #0x34
     144:      	b.lo	0x128 <_bulk_stream_kernel+0x128>
     148:      	ret
