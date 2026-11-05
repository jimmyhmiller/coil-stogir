
/Users/jimmyhmiller/Documents/Code/projects/coil-stogir/.worktrees/wide-bulk-streams/build/bulk-streams/copy416.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_bulk_stream_kernel>:
       0:      	movz	x2, #0x0, lsl #48
       4:      	b	0x20 <_bulk_stream_kernel+0x20>
       8:      	add	x3, x2, #0x10
       c:      	add	x4, x0, x2
      10:      	add	x2, x1, x2
      14:      	ldr	q0, [x2]
      18:      	str	q0, [x4]
      1c:      	mov	x2, x3
      20:      	cmp	x2, #0x1a0
      24:      	b.lo	0x8 <_bulk_stream_kernel+0x8>
      28:      	ret
