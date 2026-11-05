
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/late-bulk-vectorization/build/bulk-streams/copy416.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_bulk_stream_kernel>:
       0:      	movz	x16, #0x0, lsl #48
       4:      	lsl	x2, x16, #3
       8:      	mov	x16, #0x34              ; =52
       c:      	lsl	x3, x16, #3
      10:      	mov	x16, #0x34              ; =52
      14:      	sub	x4, x16, #0x0
      18:      	mov	x16, #0x34              ; =52
      1c:      	cmp	x16, #0x0
      20:      	cset	w5, hs
      24:      	movz	x16, #0x0, lsl #48
      28:      	mov	x17, #0x200000000000    ; =35184372088832
      2c:      	cmp	x16, x17
      30:      	cset	w6, ls
      34:      	mov	x16, #0x34              ; =52
      38:      	mov	x17, #0x200000000000    ; =35184372088832
      3c:      	cmp	x16, x17
      40:      	cset	w7, ls
      44:      	cmp	x4, #0x4
      48:      	cset	w4, hs
      4c:      	uxtb	w16, w5
      50:      	uxtb	w17, w4
      54:      	and	w4, w16, w17
      58:      	uxtb	w4, w4
      5c:      	mov	x17, #0x1000000000000   ; =281474976710656
      60:      	cmp	x0, x17
      64:      	cset	w5, lo
      68:      	add	x8, x0, x2
      6c:      	add	x9, x0, x3
      70:      	mov	x17, #0x1000000000000   ; =281474976710656
      74:      	cmp	x1, x17
      78:      	cset	w10, lo
      7c:      	add	x2, x1, x2
      80:      	add	x3, x1, x3
      84:      	uxtb	w16, w4
      88:      	uxtb	w17, w6
      8c:      	and	w4, w16, w17
      90:      	uxtb	w4, w4
      94:      	add	x6, x8, #0x0
      98:      	add	x8, x9, #0x0
      9c:      	add	x2, x2, #0x0
      a0:      	add	x3, x3, #0x0
      a4:      	uxtb	w16, w4
      a8:      	uxtb	w17, w7
      ac:      	and	w4, w16, w17
      b0:      	uxtb	w4, w4
      b4:      	mov	x17, #0x1000000000000   ; =281474976710656
      b8:      	cmp	x6, x17
      bc:      	cset	w7, lo
      c0:      	mov	x17, #0x1000000000000   ; =281474976710656
      c4:      	cmp	x8, x17
      c8:      	cset	w9, ls
      cc:      	mov	x17, #0x1000000000000   ; =281474976710656
      d0:      	cmp	x2, x17
      d4:      	cset	w11, lo
      d8:      	cmp	x8, x2
      dc:      	cset	w2, ls
      e0:      	mov	x17, #0x1000000000000   ; =281474976710656
      e4:      	cmp	x3, x17
      e8:      	cset	w8, ls
      ec:      	cmp	x3, x6
      f0:      	cset	w3, ls
      f4:      	uxtb	w16, w4
      f8:      	uxtb	w17, w10
      fc:      	and	w4, w16, w17
     100:      	uxtb	w4, w4
     104:      	uxtb	w16, w3
     108:      	uxtb	w17, w2
     10c:      	orr	w2, w16, w17
     110:      	uxtb	w2, w2
     114:      	uxtb	w16, w4
     118:      	uxtb	w17, w11
     11c:      	and	w3, w16, w17
     120:      	uxtb	w3, w3
     124:      	uxtb	w16, w3
     128:      	uxtb	w17, w8
     12c:      	and	w3, w16, w17
     130:      	uxtb	w3, w3
     134:      	uxtb	w16, w3
     138:      	uxtb	w17, w5
     13c:      	and	w3, w16, w17
     140:      	uxtb	w3, w3
     144:      	uxtb	w16, w3
     148:      	uxtb	w17, w7
     14c:      	and	w3, w16, w17
     150:      	uxtb	w3, w3
     154:      	uxtb	w16, w3
     158:      	uxtb	w17, w9
     15c:      	and	w3, w16, w17
     160:      	uxtb	w3, w3
     164:      	uxtb	w16, w3
     168:      	uxtb	w17, w2
     16c:      	and	w2, w16, w17
     170:      	uxtb	w2, w2
     174:      	uxtb	w16, w2
     178:      	cmp	w16, wzr
     17c:      	b.eq	0x1d8 <_bulk_stream_kernel+0x1d8>
     180:      	mov	x16, #0x34              ; =52
     184:      	sub	x2, x16, #0x0
     188:      	movz	x16, #0x0, lsl #48
     18c:      	lsl	x3, x16, #3
     190:      	lsr	x2, x2, #2
     194:      	add	x4, x1, x3
     198:      	add	x3, x0, x3
     19c:      	mov	x5, x3
     1a0:      	mov	x3, x2
     1a4:      	b	0x1b0 <_bulk_stream_kernel+0x1b0>
     1a8:      	add	x4, x4, #0x20
     1ac:      	add	x5, x5, #0x20
     1b0:      	sub	x3, x3, #0x1
     1b4:      	ldr	q0, [x4]
     1b8:      	str	q0, [x5]
     1bc:      	ldr	q0, [x4, #0x10]
     1c0:      	str	q0, [x5, #0x10]
     1c4:      	cmp	x3, #0x0
     1c8:      	b.ne	0x1a8 <_bulk_stream_kernel+0x1a8>
     1cc:      	lsl	x2, x2, #2
     1d0:      	add	x2, x2, #0x0
     1d4:      	b	0x1dc <_bulk_stream_kernel+0x1dc>
     1d8:      	movz	x2, #0x0, lsl #48
     1dc:      	b	0x1f8 <_bulk_stream_kernel+0x1f8>
     1e0:      	lsl	x3, x2, #3
     1e4:      	add	x2, x2, #0x1
     1e8:      	add	x4, x0, x3
     1ec:      	add	x3, x1, x3
     1f0:      	ldr	x3, [x3]
     1f4:      	str	x3, [x4]
     1f8:      	cmp	x2, #0x34
     1fc:      	b.lo	0x1e0 <_bulk_stream_kernel+0x1e0>
     200:      	ret
