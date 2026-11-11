#!/bin/zsh
# family-tests.sh FAMILY : print the paths of the facade tests of one operation
# family, one per line, from tests/X64_STATUS.md.
#
#   tools/x86/family-tests.sh floating
#   tools/x86/remote-test.sh $(tools/x86/family-tests.sh calls+ABI)
#   tools/x86/family-tests.sh all        every ported test
#   tools/x86/family-tests.sh            list the families and their sizes
set -u
ROOT=${0:A:h:h:h}
STATUS=$ROOT/tests/X64_STATUS.md
[ -f $STATUS ] || { echo "missing $STATUS; run tools/x86/test-status.py" >&2; exit 2; }
rows() { awk -F' *[|] *' '$3 == "ported-to-facade" { print $2 "|" $4 }' $STATUS; }
if [ $# -eq 0 ]; then
  rows | cut -d'|' -f2 | sort | uniq -c
  exit 0
fi
found=$(rows | awk -F'|' -v family="$1" 'family == "all" || $2 == family { print "tests/" $1 ".coil" }')
[ -n "$found" ] || { echo "no tests in family '$1'; run $0 with no argument for the list" >&2; exit 1; }
print -r -- $found
