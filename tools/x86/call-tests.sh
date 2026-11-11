#!/bin/zsh
# call-tests.sh [TEST...] : run the x86-64 call ABI tests on the Linux host.
#
# tests/x64-call-*.coil call C functions in both directions. Their C side is
# tests/x64-call-helpers.c, which this script compiles on the host with the
# system C compiler and links into every test (`--link-flag`). Without
# arguments every tests/x64-call-*.coil runs.
#
#   tools/x86/call-tests.sh
#   tools/x86/call-tests.sh tests/x64-call-abi.coil
set -u
HOST=${X86_HOST:-computer.jimmyhmiller.com}
ROOT=${0:A:h:h:h}
NAME=${ROOT:t}
DEST="stogir-x86/wt/$NAME"
cd $ROOT
if [ $# -eq 0 ]; then set -- tests/x64-call-*.coil; fi
ssh -o BatchMode=yes "$HOST" "mkdir -p $DEST/build $DEST/tests" || exit 2
rsync -a tests/x64-call-helpers.c "${HOST}:$DEST/tests/" || exit 2
ssh -o BatchMode=yes "$HOST" "cd $DEST && cc -O2 -fPIC -fno-omit-frame-pointer -Wall -c tests/x64-call-helpers.c -o build/x64-call-helpers.o" || exit 2
OBJECT=$(ssh -o BatchMode=yes "$HOST" "cd $DEST && pwd")/build/x64-call-helpers.o
COIL_FLAGS="${COIL_FLAGS:--O1 --no-debug} --link-flag $OBJECT" exec tools/x86/remote-test.sh "$@"
