#!/bin/zsh
# remote-test.sh TEST... : run library tests on the x86-64 Linux host.
#
# Copies this worktree's src/ and tests/ to the host (one directory per worktree,
# named after the worktree directory) and runs each tests/NAME.coil there with
# the Linux Coil compiler. Prints one line per test (PASS/FAIL, seconds) and the
# last lines of each failing log; exits non-zero if any test failed.
#
#   tools/x86/remote-test.sh tests/x64-encode.coil tests/jit-add.coil
#   JOBS=8 tools/x86/remote-test.sh tests/jit-*.coil
#   COIL_FLAGS="-O0" ...      compile flags (default: -O1 --no-debug)
#   X86_COIL=/path/on/host    compiler on the host (default: the LLVM-built one)
set -u
HOST=${X86_HOST:-computer.jimmyhmiller.com}
ROOT=${0:A:h:h:h}
NAME=${ROOT:t}
DEST="stogir-x86/wt/$NAME"
COMPILER=${X86_COIL:-'$HOME/stogir-x86/coil/build/x86/coil-llvm'}
FLAGS=${COIL_FLAGS:-"-O1 --no-debug"}
JOBS=${JOBS:-6}
[ $# -gt 0 ] || { echo "usage: $0 tests/NAME.coil ..." >&2; exit 2; }
ssh -o BatchMode=yes "$HOST" "mkdir -p $DEST/build/logs" || exit 2
rsync -a --delete --exclude .git --exclude build --exclude .worktrees --exclude benchmarks --exclude docs \
  "$ROOT/" "${HOST}:$DEST/" || exit 2
ssh -o BatchMode=yes "$HOST" "cd $DEST && cat > build/one.sh <<'EOS'
#!/bin/bash
n=\$(basename \$1 .coil)
s=\$(date +%s.%N)
COIL_LIBRARY_STATE=0 timeout \${TEST_TIMEOUT:-900} \$X86_COIL run \$1 \$COIL_FLAGS > build/logs/\$n.log 2>&1
rc=\$?
e=\$(date +%s.%N)
if [ \$rc = 0 ]; then printf 'PASS %s %.1fs\n' \$n \$(echo \"\$e - \$s\" | bc); else printf 'FAIL %s rc=%s %.1fs\n' \$n \$rc \$(echo \"\$e - \$s\" | bc); tail -12 build/logs/\$n.log | sed 's/^/    /'; fi
exit \$rc
EOS
chmod +x build/one.sh
export X86_COIL=$COMPILER COIL_FLAGS='$FLAGS'
printf '%s\n' $* | xargs -P $JOBS -n 1 build/one.sh"
