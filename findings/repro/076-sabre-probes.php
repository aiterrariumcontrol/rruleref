<?php
/**
 * Three sabre/vobject 4.6.1 defects, without this repository's harness.
 *
 *     php findings/repro/076-sabre-probes.php
 *
 * Needs only the adapter's composer vendor tree.
 */
require __DIR__ . '/../../conformance/adapters/php/vendor/autoload.php';

function probe(string $title, string $rrule, string $dtstart, int $n, string $expected) {
    echo "\n$title\n";
    echo "  RRULE:$rrule   DTSTART:$dtstart\n";
    $it = new \Sabre\VObject\Recur\RRuleIterator($rrule, new DateTime($dtstart));
    $out = [];
    foreach ($it as $d) {
        $out[] = $d->format('Ymd\THis');
        if (count($out) >= $n) break;
    }
    echo "  sabre : " . implode(' ', $out) . "\n";
    echo "  RFC   : $expected\n";
}

echo "sabre/vobject " . \Sabre\VObject\Version::VERSION . "\n";

probe("A  FREQ=MINUTELY has no case in RRuleIterator::next()'s switch, so the\n".
      "   date is never advanced and the iterator emits DTSTART for ever.",
      "FREQ=MINUTELY", "20260302T093015", 5,
      "20260302T093015 20260302T093115 20260302T093215 20260302T093315 20260302T093415");

probe("B  FREQ=SECONDLY, the same omission.",
      "FREQ=SECONDLY", "20260302T093015", 4,
      "20260302T093015 20260302T093016 20260302T093017 20260302T093018");

probe("C  The leap-day guard at the top of nextYearly() runs BEFORE BYYEARDAY is\n".
      "   consulted, so the first occurrence that lands on 29 February pins the\n".
      "   whole remaining series to 29 February. Day 60 is 1 March in a common\n".
      "   year and 29 February in a leap year; after 2028 sabre never returns\n".
      "   day 60 again.",
      "FREQ=YEARLY;BYYEARDAY=60", "20260301T090000", 6,
      "20260301T090000 20270301T090000 20280229T090000 20290301T090000 20300301T090000 20310301T090000");

probe("D  BYWEEKNO emits ONE day per week, not the week. The offset handed to\n".
      "   setISODate() comes from \$dayMap (SU=0..SA=6) but setISODate numbers\n".
      "   MO=1..SU=7, and with no BYDAY the branch defaults to the bare offset 1.",
      "FREQ=YEARLY;BYWEEKNO=2", "20260105T090000", 4,
      "20260105T090000 20260106T090000 20260107T090000 20260108T090000");

probe("E  The same index mismatch at BYYEARDAY, where the offsets are compared\n".
      "   against format('N'). BYDAY=SU is \$dayMap 0 and format('N') never\n".
      "   returns 0, so no day matches and the iterator walks years for ever.\n".
      "   Shown with BYDAY=MO, which survives the mismatch by coincidence.",
      "FREQ=YEARLY;BYYEARDAY=100,200;BYDAY=MO", "20260410T090000", 4,
      "(day 100 is 10 Apr, day 200 is 19 Jul; only the Mondays among them)");

probe("F  FREQ=DAILY with BYMONTH and neither BYHOUR nor BYDAY returns from\n".
      "   nextDaily()'s early-exit branch, above the loop that applies BYMONTH.",
      "FREQ=DAILY;BYMONTH=3", "20260330T090000", 5,
      "20260330T090000 20260331T090000 20270301T090000 20270302T090000 20270303T090000");
