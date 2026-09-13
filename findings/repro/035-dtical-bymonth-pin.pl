#!/usr/bin/perl
# Finding 035: DateTime::Event::ICal 0.13 reads BYMONTH at FREQ=WEEKLY and
# FREQ=MONTHLY as "month in BYMONTH *and* day-of-month = DTSTART's day".
#
# Needs only DateTime::Event::ICal (Debian: libdatetime-event-ical-perl).
# Nothing from the rruleref repository.
#
#   perl findings/repro/035-dtical-bymonth-pin.pl
#
# Exits non-zero if any of the six claims below stops holding.

use strict;
use warnings;
use DateTime;
use DateTime::Event::ICal;
use DateTime::Event::Recurrence;

my $fail = 0;
sub claim {
    my ($name, $ok) = @_;
    printf "%-6s %s\n", ($ok ? "ok" : "FAIL"), $name;
    $fail++ unless $ok;
}

# Expand a recurrence to at most $n occurrences as YYYYMMDD, or the die message.
sub take {
    my ($n, %args) = @_;
    my @o;
    eval {
        my $it = DateTime::Event::ICal->recur(%args)->iterator;
        while (@o < $n) { my $d = $it->next; last unless defined $d; push @o, $d->ymd(''); }
        1;
    } or return "DIED: $@";
    return join ' ', @o;
}

my $DT = DateTime->new(year => 2020, month => 1, day => 6, hour => 9);  # a Monday, day 6

print "== 1. the pin at FREQ=WEEKLY ==\n";
my $w = take(6, dtstart => $DT, freq => 'weekly',
                bymonth => [1, 3], byday => ['mo', 'we']);
print "  FREQ=WEEKLY;BYMONTH=1,3;BYDAY=MO,WE  DTSTART 2020-01-06\n    $w\n";
print "  correct (python-dateutil, rrule.js, dmfs lib-recur, libical):\n";
print "    20200106 20200108 20200113 20200115 20200120 20200122\n";
claim("every WEEKLY occurrence falls on day-of-month 06 = DTSTART's",
      (scalar(grep { /^\d{6}06$/ } split ' ', $w) == 6));

print "\n== 2. the same pin at FREQ=MONTHLY ==\n";
my $m = take(6, dtstart => $DT, freq => 'monthly',
                bymonth => [1, 3], byday => ['mo']);
print "  FREQ=MONTHLY;BYMONTH=1,3;BYDAY=MO         $m\n";
claim("every MONTHLY+BYDAY occurrence falls on day-of-month 06",
      (scalar(grep { /^\d{6}06$/ } split ' ', $m) == 6));

# Without BYDAY the pin coincides with the correct answer, so MONTHLY looks fine.
my $m2 = take(4, dtstart => $DT, freq => 'monthly', bymonth => [1, 3]);
print "  FREQ=MONTHLY;BYMONTH=1,3 (no BYDAY)      $m2\n";
claim("MONTHLY without BYDAY is correct -- the pin coincides",
      $m2 eq '20200106 20200306 20210106 20210306');

print "\n== 3. DAILY and YEARLY are controls: they are correct ==\n";
my $d = take(4, dtstart => $DT, freq => 'daily', bymonth => [1, 3]);
my $y = take(4, dtstart => $DT, freq => 'yearly', bymonth => [1, 3], byday => ['mo']);
print "  FREQ=DAILY;BYMONTH=1,3                   $d\n";
print "  FREQ=YEARLY;BYMONTH=1,3;BYDAY=MO         $y\n";
claim("DAILY is correct (_daily_recurrence carries the [1..31] workaround)",
      $d eq '20200106 20200107 20200108 20200109');
claim("YEARLY is correct (no handler deletes what the filter needs)",
      $y eq '20200106 20200113 20200120 20200127');

print "\n== 4. supplying the missing default by hand fixes WEEKLY ==\n";
my $wf = take(6, dtstart => $DT, freq => 'weekly',
                 bymonth => [1, 3], byday => ['mo', 'we'],
                 bymonthday => [1 .. 31]);
print "  ... the same call with bymonthday => [1..31]\n    $wf\n";
claim("with bymonthday => [1..31] the WEEKLY answer is correct",
      $wf eq '20200106 20200108 20200113 20200115 20200120 20200122');

print "\n== 5. the Recurrence.pm line-822 crash is downstream of the pin ==\n";
# DTSTART 2026-03-31; the pinned day 31 does not exist in February.
my $DC = DateTime->new(year => 2026, month => 3, day => 31, hour => 9);
my $c1 = take(3, dtstart => $DC, freq => 'weekly',
                 bymonth => [2, 3], byday => ['th', 'tu', 'we']);
my $c2 = take(3, dtstart => $DC, freq => 'weekly',
                 bymonth => [2, 3], byday => ['th', 'tu', 'we'],
                 bymonthday => [1 .. 31]);
printf "  as parsed              %s\n", ($c1 =~ /^DIED/ ? "dies: Recurrence.pm line 822" : $c1);
printf "  + bymonthday=>[1..31]  %s\n", $c2;
claim("the unpatched call dies at Recurrence.pm line 822",
      $c1 =~ /line 822/);
claim("the same call with the workaround returns occurrences",
      $c2 !~ /^DIED/ && $c2 =~ /^\d{8} /);

print "\n== 6. the residual: a second defect, in DateTime::Event::Recurrence ==\n";
# The pin puts a 29 in days when DTSTART is 29 February. Then this bites.
for my $day (29, 28) {
    my $set = DateTime::Event::Recurrence->yearly(
        months => [2, 3], days => $day,
        hours => 9, minutes => 0, seconds => 0,
        start => DateTime->new(year => 2024, month => 2, day => $day, hour => 9));
    my $it = $set->iterator(span => DateTime::Span->from_datetimes(
        start => DateTime->new(year => 2024, month => 1, day => 1)));
    my @o;
    for (1 .. 6) { my $n = $it->next; last unless $n; push @o, $n->ymd(''); }
    printf "  yearly(months=>[2,3], days=>%d)  %s\n", $day, join(' ', @o);
    if ($day == 29) {
        claim("with days=>29, March never appears in any year",
              !grep { /^\d{4}03/ } @o);
    } else {
        claim("with days=>28, March appears -- so it is day 29, not the months",
              scalar(grep { /^\d{4}03/ } @o) > 0);
    }
}

print "\n";
if ($fail) { print "$fail claim(s) FAILED\n"; exit 1 }
print "all claims hold\n";
exit 0;
