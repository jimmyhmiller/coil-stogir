
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/late-bulk-vectorization/build/bulk-streams/copy416.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_bulk_stream_kernel>:
       0:      	mov	x16, #0x1a0             ; =416
       4:      	lsr	x2, x16, #3
       8:      	movz	x16, #0x0, lsl #48
       c:      	lsl	x3, x16, #3
      10:      	movz	x16, #0x0, lsl #48
      14:      	mov	x17, #0x200000000000    ; =35184372088832
      18:      	cmp	x16, x17
      1c:      	cset	w4, ls
      20:      	lsl	x5, x2, #3
      24:      	sub	x6, x2, #0x0
      28:      	cmp	x2, #0x0
      2c:      	cset	w7, hs
      30:      	mov	x17, #0x200000000000    ; =35184372088832
      34:      	cmp	x2, x17
      38:      	cset	w8, ls
      3c:      	cmp	x6, #0x4
      40:      	cset	w6, hs
      44:      	mov	x17, #0x1000000000000   ; =281474976710656
      48:      	cmp	x0, x17
      4c:      	cset	w9, lo
      50:      	add	x10, x0, x3
      54:      	add	x11, x0, x5
      58:      	mov	x17, #0x1000000000000   ; =281474976710656
      5c:      	cmp	x1, x17
      60:      	cset	w12, lo
      64:      	add	x3, x1, x3
      68:      	add	x5, x1, x5
      6c:      	uxtb	w16, w7
      70:      	uxtb	w17, w6
      74:      	and	w6, w16, w17
      78:      	uxtb	w6, w6
      7c:      	add	x7, x10, #0x0
      80:      	add	x10, x11, #0x0
      84:      	add	x3, x3, #0x0
      88:      	add	x5, x5, #0x0
      8c:      	uxtb	w16, w6
      90:      	uxtb	w17, w4
      94:      	and	w4, w16, w17
      98:      	uxtb	w4, w4
      9c:      	mov	x17, #0x1000000000000   ; =281474976710656
      a0:      	cmp	x7, x17
      a4:      	cset	w6, lo
      a8:      	mov	x17, #0x1000000000000   ; =281474976710656
      ac:      	cmp	x10, x17
      b0:      	cset	w11, ls
      b4:      	mov	x17, #0x1000000000000   ; =281474976710656
      b8:      	cmp	x3, x17
      bc:      	cset	w13, lo
      c0:      	cmp	x10, x3
      c4:      	cset	w3, ls
      c8:      	mov	x17, #0x1000000000000   ; =281474976710656
      cc:      	cmp	x5, x17
      d0:      	cset	w10, ls
      d4:      	cmp	x5, x7
      d8:      	cset	w5, ls
      dc:      	uxtb	w16, w4
      e0:      	uxtb	w17, w8
      e4:      	and	w4, w16, w17
      e8:      	uxtb	w4, w4
      ec:      	uxtb	w16, w5
      f0:      	uxtb	w17, w3
      f4:      	orr	w3, w16, w17
      f8:      	uxtb	w3, w3
      fc:      	uxtb	w16, w4
     100:      	uxtb	w17, w12
     104:      	and	w4, w16, w17
     108:      	uxtb	w4, w4
     10c:      	uxtb	w16, w4
     110:      	uxtb	w17, w13
     114:      	and	w4, w16, w17
     118:      	uxtb	w4, w4
     11c:      	uxtb	w16, w4
     120:      	uxtb	w17, w10
     124:      	and	w4, w16, w17
     128:      	uxtb	w4, w4
     12c:      	uxtb	w16, w4
     130:      	uxtb	w17, w9
     134:      	and	w4, w16, w17
     138:      	uxtb	w4, w4
     13c:      	uxtb	w16, w4
     140:      	uxtb	w17, w6
     144:      	and	w4, w16, w17
     148:      	uxtb	w4, w4
     14c:      	uxtb	w16, w4
     150:      	uxtb	w17, w11
     154:      	and	w4, w16, w17
     158:      	uxtb	w4, w4
     15c:      	uxtb	w16, w4
     160:      	uxtb	w17, w3
     164:      	and	w3, w16, w17
     168:      	uxtb	w3, w3
     16c:      	uxtb	w16, w3
     170:      	cmp	w16, wzr
     174:      	b.eq	0x1d0 <_bulk_stream_kernel+0x1d0>
     178:      	sub	x3, x2, #0x0
     17c:      	movz	x16, #0x0, lsl #48
     180:      	lsl	x4, x16, #3
     184:      	lsr	x3, x3, #2
     188:      	add	x5, x1, x4
     18c:      	add	x4, x0, x4
     190:      	mov	x6, x4
     194:      	mov	x4, x3
     198:      	b	0x1a8 <_bulk_stream_kernel+0x1a8>
     19c:      	nop
     1a0:      	add	x5, x5, #0x20
     1a4:      	add	x6, x6, #0x20
     1a8:      	sub	x4, x4, #0x1
     1ac:      	ldr	q0, [x5]
     1b0:      	str	q0, [x6]
     1b4:      	ldr	q0, [x5, #0x10]
     1b8:      	str	q0, [x6, #0x10]
     1bc:      	cmp	x4, #0x0
     1c0:      	b.ne	0x1a0 <_bulk_stream_kernel+0x1a0>
     1c4:      	lsl	x3, x3, #2
     1c8:      	add	x3, x3, #0x0
     1cc:      	b	0x1d4 <_bulk_stream_kernel+0x1d4>
     1d0:      	movz	x3, #0x0, lsl #48
     1d4:      	b	0x1f0 <_bulk_stream_kernel+0x1f0>
     1d8:      	lsl	x4, x3, #3
     1dc:      	add	x3, x3, #0x1
     1e0:      	add	x5, x0, x4
     1e4:      	add	x4, x1, x4
     1e8:      	ldr	x4, [x4]
     1ec:      	str	x4, [x5]
     1f0:      	cmp	x3, x2
     1f4:      	b.lo	0x1d8 <_bulk_stream_kernel+0x1d8>
     1f8:      	ret
