#!/bin/sh
# 043: sabre/vobject's FREQ=HOURLY ignores every BY* part.
# sabre's output is identical for all seven rules below; the control's is not.
# Run from the repository root. Requires the php adapter (composer install).
set -e
R=$(cd "$(dirname "$0")/../.." && pwd)
for RULE in "FREQ=HOURLY;BYMONTH=1" "FREQ=HOURLY;BYMONTHDAY=1" \
            "FREQ=HOURLY;BYYEARDAY=1" "FREQ=HOURLY;BYSETPOS=1" \
            "FREQ=HOURLY;BYDAY=MO" "FREQ=HOURLY;BYMINUTE=0,30" \
            "FREQ=HOURLY;BYHOUR=9,10"; do
  IN="{\"id\":\"t\",\"rrule\":\"$RULE\",\"dtstart\":\"20260101T090000\",\"limit\":5}"
  printf '%-28s sabre: ' "$RULE"
  echo "$IN" | (cd "$R/conformance/adapters/php" && php vobject_adapter.php)
  printf '%-28s ctl:   ' ""
  echo "$IN" | python3 "$R/conformance/adapters/dateutil_adapter.py"
done
