<?php
/**
 * The two sabre/vobject 4.6.1 defects of finding 086, without this
 * repository's harness.
 *
 *     php findings/repro/086-sabre-probes.php
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

probe("A  nextWeekly() advances by ONE HOUR when the rule carries BYHOUR, and the\n".
      "   week rollover it then looks for can only fire at hour 0 of the first day\n".
      "   of the week -- a no-op at INTERVAL=1. So a weekly rule becomes a DAILY\n".
      "   one: this asks for 9 o'clock once a week and gets 9 o'clock every day.\n".
      "   Unlike every other defect in finding 076, this ADDS occurrences.",
      "FREQ=WEEKLY;BYHOUR=9", "20260302T090000", 6,
      "20260302T090000 20260309T090000 20260316T090000 20260323T090000 20260330T090000 20260406T090000");

probe("B  nextYearly()'s BYMONTH branch walks the month number and then calls\n".
      "   setDate() with the day number it already had. PHP's setDate() overflows\n".
      "   rather than rejecting, so 29 February in a common year becomes 1 March --\n".
      "   and the day number for every later occurrence is then 1.",
      "FREQ=YEARLY;INTERVAL=2;BYMONTH=2", "20240229T090000", 6,
      "20240229T090000 20280229T090000 20320229T090000 20360229T090000 20400229T090000 20440229T090000");

probe("B' The same rule at INTERVAL=4 is CORRECT for nineteen occurrences, because\n".
      "   every step lands in a leap year -- until 2100, which is divisible by 100\n".
      "   and not by 400. Ten lines of comment in the method above this one explain\n".
      "   why the leap-day guard must not just add multiples of four, and name 2100.\n".
      "   This branch has no such care: watch position 20 and everything after it.",
      "FREQ=YEARLY;INTERVAL=4;BYMONTH=2", "20240229T090000", 22,
      "... 20960229T090000 21040229T090000 21080229T090000   (2100 is not a leap year, so 3.3.10 gives nothing there)");

probe("C  getMonthlyOccurrences() is called for ONE month and applies BYSETPOS\n".
      "   inside it, so at FREQ=YEARLY the set BYSETPOS counts within is the month,\n".
      "   not the year. 'the 2nd Wednesday of September-or-November' becomes 'the\n".
      "   2nd Wednesday of September AND the 2nd Wednesday of November'.",
      "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2", "20270908T090000", 6,
      "20270908T090000 20280913T090000 20290912T090000 20300911T090000 20310910T090000 20320908T090000");
