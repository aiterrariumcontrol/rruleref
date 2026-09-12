#!/usr/bin/perl
# Finding 030. Two probes against DateTime::Event::ICal 0.13, no harness.
#
#   sudo apt-get install -y libdatetime-event-ical-perl
#   TZ=UTC perl 030-dtical-dtstart-fill.pl
use strict;
use warnings;
use DateTime;
use DateTime::Event::ICal;

sub first {
    my ($n, %args) = @_;
    my $out = eval {
        my $it = DateTime::Event::ICal->recur(%args)->iterator;
        join ' ', map { my $d = $it->next; $d ? $d->ymd : 'undef' } 1 .. $n;
    };
    if (!defined $out) { my $e = $@; $e =~ s/\s+$//; return "ERROR: $e" }
    return $out;
}

print "1. The DTSTART fill, in the two branches RFC 5545 \xc2\xa73.3.10 leaves open\n\n";

# BYMONTHDAY with no BYMONTH. The table says expand over all twelve months;
# the DTSTART-fill sentence says take the month from DTSTART.
print "   FREQ=YEARLY;BYMONTHDAY=-1  DTSTART 2026-03-31\n     ",
    first(4, dtstart => DateTime->new(year=>2026,month=>3,day=>31,hour=>9),
             freq => 'yearly', bymonthday => [-1]),
    "\n     (all March: BYMONTH filled from DTSTART, not expanded)\n\n";

# BYWEEKNO with no BYDAY. Same two readings, the other field.
print "   FREQ=YEARLY;BYWEEKNO=-2,-1  DTSTART 2026-12-21 (a Monday)\n     ",
    first(4, dtstart => DateTime->new(year=>2026,month=>12,day=>21,hour=>9),
             freq => 'yearly', byweekno => [-2,-1]),
    "\n     (all Mondays: BYDAY filled from DTSTART, not expanded over the week)\n",
    "     ISO 2026 has 53 weeks and 2027 has 52, and both are counted from the\n",
    "     end correctly, so this is the fill and not a week-arithmetic bug.\n\n";

print "2. The same fill, crashing, when the filled day does not exist\n\n";
for my $day (31, 30) {
    printf "   FREQ=MONTHLY;BYMONTH=11,12  DTSTART 2026-12-%02d\n     %s\n",
        $day,
        first(3, dtstart => DateTime->new(year=>2026,month=>12,day=>$day,hour=>9),
                 freq => 'monthly', bymonth => [11,12]);
}
print "\n   BYMONTHDAY is filled with day-of-month 31 from DTSTART; November has\n",
      "   no 31st; the resulting set is undefined and the iterator dies.\n",
      "   This is the smallest reproducer of the crash site, not the whole\n",
      "   story: 65 corpus cases die at Recurrence.pm line 822, and only 8 of\n",
      "   them have a selected day that cannot exist. The other 57 share the\n",
      "   crash site with a different route to an undefined set.\n";
