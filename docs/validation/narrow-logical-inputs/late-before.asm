
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/late-bulk-vectorization/build/bulk-streams/copy416.o:	file format mach-o arm64

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
      30:      	uxtb	w16, w5
      34:      	and	w5, w16, #0x1
      38:      	uxtb	w5, w5
      3c:      	add	x6, x6, #0x0
      40:      	add	x7, x7, #0x0
      44:      	mov	x17, #0x1000000000000   ; =281474976710656
      48:      	cmp	x3, x17
      4c:      	cset	w8, lo
      50:      	mov	x17, #0x1000000000000   ; =281474976710656
      54:      	cmp	x4, x17
      58:      	cset	w9, ls
      5c:      	mov	x17, #0x1000000000000   ; =281474976710656
      60:      	cmp	x6, x17
      64:      	cset	w10, lo
      68:      	cmp	x4, x6
      6c:      	cset	w4, ls
      70:      	mov	x17, #0x1000000000000   ; =281474976710656
      74:      	cmp	x7, x17
      78:      	cset	w6, ls
      7c:      	cmp	x7, x3
      80:      	cset	w3, ls
      84:      	uxtb	w16, w5
      88:      	uxtb	w17, w10
      8c:      	and	w5, w16, w17
      90:      	uxtb	w5, w5
      94:      	uxtb	w16, w4
      98:      	uxtb	w17, w3
      9c:      	orr	w3, w16, w17
      a0:      	uxtb	w3, w3
      a4:      	uxtb	w16, w5
      a8:      	uxtb	w17, w6
      ac:      	and	w4, w16, w17
      b0:      	uxtb	w4, w4
      b4:      	uxtb	w16, w2
      b8:      	uxtb	w17, w4
      bc:      	and	w2, w16, w17
      c0:      	uxtb	w2, w2
      c4:      	uxtb	w16, w2
      c8:      	uxtb	w17, w8
      cc:      	and	w2, w16, w17
      d0:      	uxtb	w2, w2
      d4:      	uxtb	w16, w2
      d8:      	uxtb	w17, w9
      dc:      	and	w2, w16, w17
      e0:      	uxtb	w2, w2
      e4:      	uxtb	w16, w3
      e8:      	uxtb	w17, w2
      ec:      	and	w2, w16, w17
      f0:      	uxtb	w2, w2
      f4:      	uxtb	w16, w2
      f8:      	cmp	w16, wzr
      fc:      	b.eq	0x158 <_bulk_stream_kernel+0x158>
     100:      	mov	x16, #0x34              ; =52
     104:      	sub	x2, x16, #0x0
     108:      	movz	x16, #0x0, lsl #48
     10c:      	lsl	x3, x16, #3
     110:      	lsr	x2, x2, #2
     114:      	add	x4, x1, x3
     118:      	add	x3, x0, x3
     11c:      	mov	x5, x3
     120:      	mov	x3, x2
     124:      	b	0x130 <_bulk_stream_kernel+0x130>
     128:      	add	x4, x4, #0x20
     12c:      	add	x5, x5, #0x20
     130:      	sub	x3, x3, #0x1
     134:      	ldr	q0, [x4]
     138:      	str	q0, [x5]
     13c:      	ldr	q0, [x4, #0x10]
     140:      	str	q0, [x5, #0x10]
     144:      	cmp	x3, #0x0
     148:      	b.ne	0x128 <_bulk_stream_kernel+0x128>
     14c:      	lsl	x2, x2, #2
     150:      	add	x2, x2, #0x0
     154:      	b	0x15c <_bulk_stream_kernel+0x15c>
     158:      	movz	x2, #0x0, lsl #48
     15c:      	b	0x178 <_bulk_stream_kernel+0x178>
     160:      	lsl	x3, x2, #3
     164:      	add	x2, x2, #0x1
     168:      	add	x4, x0, x3
     16c:      	add	x3, x1, x3
     170:      	ldr	x3, [x3]
     174:      	str	x3, [x4]
     178:      	cmp	x2, #0x34
     17c:      	b.lo	0x160 <_bulk_stream_kernel+0x160>
     180:      	ret
