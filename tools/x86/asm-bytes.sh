#!/bin/zsh
# asm-bytes.sh [FILE.s] : assemble x86-64 assembly (Intel syntax, from FILE.s or
# stdin) with GNU as on the x86-64 Linux host and print the bytes as Coil
# literals, twelve per line, ready for (primitive/machine-code (X86_64) ...).
# Test probe functions get their bytes from here, never from hand encoding.
#
#   print 'movups xmm0, [rsi]\ncall rdi' | tools/x86/asm-bytes.sh
set -eu
HOST=${X86_HOST:-computer.jimmyhmiller.com}
{ print '.intel_syntax noprefix'; print '.text'; cat ${1:-/dev/stdin}; } |
  ssh -o BatchMode=yes "$HOST" 'd=$(mktemp -d) && cat > $d/a.s && as --64 -o $d/a.o $d/a.s && objcopy -O binary -j .text $d/a.o $d/a.bin && od -An -v -tx1 $d/a.bin | tr -s " \n" "\n" | sed "/^$/d; s/^/0x/" | paste -sd " " | fold -s -w 60; echo; rm -rf $d'
