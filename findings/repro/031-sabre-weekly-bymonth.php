<?php
// Finding 031, cause 1: sabre/vobject ignores BYMONTH at FREQ=WEEKLY and FREQ=MONTHLY.
// No harness. Requires only sabre/vobject.
//   composer require sabre/vobject && php 031-sabre-weekly-bymonth.php
require __DIR__ . '/../../conformance/adapters/php/vendor/autoload.php';

use Sabre\VObject\Recur\RRuleIterator;

function first(string $rrule, string $dtstart, int $n): array {
    $it = new RRuleIterator($rrule, new DateTime($dtstart));
    $out = [];
    foreach ($it as $d) { $out[] = $d->format('Ymd'); if (count($out) >= $n) break; }
    return $out;
}

// BYMONTH=5,10 must confine occurrences to May and October.
$r = 'FREQ=WEEKLY;BYDAY=FR,SU;BYMONTH=5,10';
echo "$r  DTSTART=20260517\n";
echo "  sabre : " . implode(' ', first($r, '20260517T090000', 6)) . "\n";
echo "  RFC   : 20260517 20260522 20260524 20260529 20260531 20261002\n";
echo "  (sabre runs straight into June; BYMONTH had no effect)\n\n";

// Identical rule with BYMONTH deleted -> sabre gives the same answer.
$r2 = 'FREQ=WEEKLY;BYDAY=FR,SU';
echo "$r2  (BYMONTH deleted)\n";
echo "  sabre : " . implode(' ', first($r2, '20260517T090000', 6)) . "\n\n";

// Same omission at MONTHLY.
$r3 = 'FREQ=MONTHLY;BYMONTHDAY=15;BYMONTH=3,9';
echo "$r3  DTSTART=20260315\n";
echo "  sabre : " . implode(' ', first($r3, '20260315T090000', 4)) . "\n";
echo "  RFC   : 20260315 20260915 20270315 20270915\n\n";

// But BYMONTH *is* honoured at YEARLY, so this is frequency-specific.
$r4 = 'FREQ=YEARLY;BYMONTH=3,9;BYMONTHDAY=15';
echo "$r4  DTSTART=20260315\n";
echo "  sabre : " . implode(' ', first($r4, '20260315T090000', 4)) . "\n";
echo "  RFC   : 20260315 20260915 20270315 20270915\n";
