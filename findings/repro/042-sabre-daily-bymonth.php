<?php
// 042 — sabre/vobject applies BYMONTH at FREQ=DAILY only when BYDAY or BYHOUR
// is also present. Run from conformance/adapters/php after `composer install`:
//   php ../../../findings/repro/042-sabre-daily-bymonth.php
require __DIR__ . '/../../conformance/adapters/php/vendor/autoload.php';

function show(string $rrule, string $dtstart, int $n): void {
    $it = new \Sabre\VObject\Recur\RRuleIterator($rrule, new \DateTime($dtstart));
    $out = [];
    foreach ($it as $d) { $out[] = $d->format('Ymd'); if (count($out) >= $n) break; }
    printf("%-34s %s\n", $rrule, implode(' ', $out));
}

// BYMONTH ignored: the fast path in nextDaily() returns before the filter loop.
show('FREQ=DAILY;BYMONTH=1', '20270101T090000', 10);
// BYDAY present: the same rule now honours BYMONTH and jumps to January 2028.
show('FREQ=DAILY;BYMONTH=1;BYDAY=MO', '20270104T090000', 10);
