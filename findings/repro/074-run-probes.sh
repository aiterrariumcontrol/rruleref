#!/bin/sh
# Minimal reproducers for finding 074's defects, run against every adapter that
# answers in seconds. Each probe is a one-line RRULE, so a disagreement here is
# not an artifact of the corpus or of the scorer -- score.py is not involved.
#
#   sh findings/repro/074-run-probes.sh > /tmp/074-probes.txt
#
# Run from the repository root. dtical is omitted deliberately: it is minutes
# per run and none of these defects is about it.
set -e
P=findings/repro/074-probes.ndjson
CP="conformance/adapters/java/classes:$(ls conformance/adapters/java/libs/*.jar | tr '\n' ':')"
for a in "node conformance/adapters/icaljs_adapter.js" \
         "python3 conformance/adapters/dateutil_adapter.py" \
         "node conformance/adapters/rrulejs_adapter.js" \
         "conformance/adapters/rust/target/release/rustrrule_adapter" \
         "php conformance/adapters/php/vobject_adapter.php" \
         "java -Duser.language=en -Duser.country=US -cp $CP Ical4jAdapter" \
         "java -Duser.language=en -Duser.country=GB -cp $CP DmfsAdapter"; do
  echo "=== $a"
  TZ=UTC $a < "$P" 2>/dev/null
done
