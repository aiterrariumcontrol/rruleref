#!/bin/bash
# Run every built adapter over the 20 DATE-value-type protocol cases.
set -u
R=/home/agent/terrarium/projects/rruleref
O=/home/agent/terrarium/scratch/dvt-audit
D=/home/agent/terrarium/scratch/disputed-audit
IN=$O/dvt_cases.ndjson
CP="$R/conformance/adapters/java/classes:$R/conformance/adapters/java/libs/*"
CP430="$R/conformance/adapters/java/classes:$R/conformance/adapters/java/libs430/*:$R/conformance/adapters/java/libs/*"

run() { name=$1; shift; echo "--- $name"; timeout 1800 "$@" < "$IN" > "$O/out.$name.ndjson" 2>"$O/err.$name.log"; echo "  rc=$? lines=$(wc -l < "$O/out.$name.ndjson")"; }

cd "$R"
export TZ=UTC
run dateutil      python3 conformance/adapters/dateutil_adapter.py
run rrulejs       node conformance/adapters/rrulejs_adapter.js
run icaljs        node conformance/adapters/icaljs_adapter.js
run ical4j411     java -Duser.language=en -Duser.country=GB -cp "$CP"    Ical4jAdapter
run ical4j430     java -Duser.language=en -Duser.country=GB -cp "$CP430" Ical4jAdapter
run dmfs          java -cp "$CP" DmfsAdapter
run libical_3020  "$D/libical_adapter_3020"
LD_LIBRARY_PATH=/home/agent/terrarium/scratch/libical-install/lib \
  run libical_48d5 conformance/adapters/c/libical_adapter
LD_LIBRARY_PATH=/home/agent/terrarium/scratch/libical-install-4edd/lib \
  run libical_4edd conformance/adapters/c/libical_adapter
run rrulego       "$D/rrulego_adapter"
run rustrrule     conformance/adapters/rust/target/release/rustrrule_adapter
run sabre         php conformance/adapters/php/vobject_adapter.php
run dtical        perl conformance/adapters/perl/dtical_adapter.pl
