#!/bin/sh
# 044: two unrelated FREQ=YEARLY defects in sabre/vobject 4.6.1.
#  (1) BYSETPOS is dropped on the BYYEARDAY and BYWEEKNO branches, and applied
#      per-month rather than per-year on the BYMONTH branch.
#  (2) FREQ=YEARLY;INTERVAL=4;BYMONTH=2 from a Feb 29 DTSTART overflows at 2100
#      and never returns to Feb 29; without BYMONTH the same rule is correct.
# Run from anywhere. Requires the php adapter (composer install) and python3.
set -e
R=$(cd "$(dirname "$0")/../.." && pwd)
run() { # rule dtstart limit
  IN="{\"id\":\"t\",\"rrule\":\"$1\",\"dtstart\":\"$2\",\"limit\":$3}"
  echo "$1  (DTSTART $2)"
  printf '  sabre:   '; echo "$IN" | (cd "$R/conformance/adapters/php" && php vobject_adapter.php)
  printf '  control: '; echo "$IN" | python3 "$R/conformance/adapters/dateutil_adapter.py"
}
echo '== BYSETPOS dropped: these three are byte-identical in sabre =='
run "FREQ=YEARLY;BYYEARDAY=-60,1;BYDAY=SA,TH;BYSETPOS=-1" 20281102T090000 18
run "FREQ=YEARLY;BYYEARDAY=-60,1;BYDAY=SA,TH;BYSETPOS=1"  20281102T090000 18
run "FREQ=YEARLY;BYYEARDAY=-60,1;BYDAY=SA,TH"             20281102T090000 18
echo
echo '== BYSETPOS applied to the wrong set (per month, not per year) =='
run "FREQ=YEARLY;BYMONTH=1,2;BYDAY=MO;BYSETPOS=-1"        20270104T090000 8
run "FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO,TU;BYSETPOS=-1"     20270517T090000 6
echo
echo '== leap day: BYMONTH makes the correct rule wrong =='
run "FREQ=YEARLY;INTERVAL=4"                              20960229T090000 6
run "FREQ=YEARLY;INTERVAL=4;BYMONTH=2"                    20960229T090000 6
