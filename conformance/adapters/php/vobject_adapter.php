<?php
// Adapter for sabre/vobject's RRuleIterator. See ../../PROTOCOL.md.
//
// Reads one JSON case per line on stdin, writes one JSON result per line.
// Everything in the corpus is floating local time; the process is expected to
// run under TZ=UTC so that no timezone database can enter an answer.

require __DIR__ . '/vendor/autoload.php';

use Sabre\VObject\Recur\RRuleIterator;

function parse_dtstart(string $s): DateTimeImmutable
{
    // YYYYMMDDTHHMMSS, floating.
    $d = DateTimeImmutable::createFromFormat('Ymd\THis', $s, new DateTimeZone(date_default_timezone_get()));
    if (false === $d) {
        throw new InvalidArgumentException("bad dtstart: $s");
    }
    return $d;
}

// A case that does not terminate is a result, not a crash: give each one a
// hard wall-clock deadline and report the timeout in the error column. See the
// README for why this is needed at all.
$deadline = (int) (getenv('RRULE_CASE_TIMEOUT') ?: 10);
pcntl_async_signals(true);
pcntl_signal(SIGALRM, function () use (&$deadline) {
    throw new RuntimeException("no answer within {$deadline}s");
});

$out = fopen('php://stdout', 'w');
while (false !== ($line = fgets(STDIN))) {
    $line = trim($line);
    if ('' === $line) {
        continue;
    }
    $case = json_decode($line, true, 512, JSON_THROW_ON_ERROR);
    $id = $case['id'];
    $limit = (int) $case['limit'];
    try {
        pcntl_alarm($deadline);
        $start = parse_dtstart($case['dtstart']);
        $it = new RRuleIterator($case['rrule'], $start);
        $occ = [];
        while ($it->valid() && count($occ) < $limit) {
            $occ[] = $it->current()->format('Ymd\THis');
            $it->next();
        }
        $res = ['id' => $id, 'occurrences' => $occ];
    } catch (Throwable $e) {
        $res = ['id' => $id, 'error' => get_class($e) . ': ' . $e->getMessage()];
    }
    pcntl_alarm(0);
    fwrite($out, json_encode($res, JSON_UNESCAPED_SLASHES) . "\n");
}
