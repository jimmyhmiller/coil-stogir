
/tmp/coil-stogir-inline-vector.o:	file format mach-o arm64

Disassembly of section __TEXT,__text:

0000000000000000 <_internal_vector_caller>:
       0:      	ldr	q0, [x1]
       4:      	adrp	x17, 0x0 <_internal_vector_caller>
		0000000000000004:  ARM64_RELOC_PAGE21	L_stogir_0000000000000000
       8:      	add	x17, x17, #0x0
		0000000000000008:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000000
       c:      	ldr	q31, [x17]
      10:      	eor.16b	v0, v0, v31
      14:      	str	q0, [x0]
      18:      	mov	x0, #0x25               ; =37
      1c:      	ret

0000000000000020 <_internal_vector_leaf>:
      20:      	ldr	q0, [x1]
      24:      	adrp	x17, 0x0 <_internal_vector_caller>
		0000000000000024:  ARM64_RELOC_PAGE21	L_stogir_0000000000000001
      28:      	add	x17, x17, #0x0
		0000000000000028:  ARM64_RELOC_PAGEOFF12	L_stogir_0000000000000001
      2c:      	ldr	q31, [x17]
      30:      	eor.16b	v0, v0, v31
      34:      	str	q0, [x0]
      38:      	mov	x0, #0x25               ; =37
      3c:      	ret
