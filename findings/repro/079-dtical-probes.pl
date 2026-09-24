#!/usr/bin/perl
# Standalone demonstration for finding 079.  Needs DateTime::Event::ICal and
# nothing from this repository.
#
#     perl findings/repro/079-dtical-probes.pl
use strict;
use warnings;
use DateTime;
use DateTime::Event::ICal;

sub show {
    my ($label, $rule, $dtstart, %args) = @_;
    print "$label\n  RRULE:$rule\n  DTSTART:", $dtstart->strftime('%Y%m%dT%H%M%S'), "\n  ";
    my @out;
    eval {
        local $SIG{ALRM} = sub { die "no answer within 20s\n" };
        alarm 20;
        my $set = DateTime::Event::ICal->recur(dtstart => $dtstart, %args);
        my $it = $set->iterator;
        while (@out < 5) { my $d = $it->next; last unless defined $d;
                           push @out, $d->strftime('%Y-%m-%d'); }
        alarm 0; 1;
    } or do { alarm 0; my $e = $@; $e =~ s/\s+$//; print "DIED: $e\n\n"; return };
    print join(', ', @out), "\n\n";
}

my $d = DateTime->new(year=>2026, month=>3, day=>2, hour=>9);

# 1 -- the month is not in the rule, so it is taken from DTSTART: "the 15th of
#      every month" becomes "the 15th of March, once a year".
show('1  bare BYMONTHDAY: the month comes from DTSTART',
     'FREQ=DAILY;BYMONTHDAY=15', $d, freq=>'daily', bymonthday=>[15]);

# ...but at MONTHLY the base handler consumes BYMONTHDAY itself, so no
# auxiliary set is built and there is no gap to fill.  This one is correct.
show('1b at MONTHLY the same part is consumed by the base handler (correct)',
     'FREQ=MONTHLY;BYMONTHDAY=15', $d, freq=>'monthly', bymonthday=>[15]);

# 2 -- BYWEEKNO is routed to _weekly_recurrence, which never reads it, and the
#      day and weekday are both filled from DTSTART.
show('2  BYWEEKNO discarded unread, day and weekday filled from DTSTART',
     'FREQ=YEARLY;BYMONTH=3;BYWEEKNO=10', $d,
     freq=>'yearly', bymonth=>[3], byweekno=>[10]);

# 3 -- byminute survives every delete and reaches the die at the end of recur().
show('3  a time-of-day part at MINUTELY is fatal',
     'FREQ=MINUTELY;BYMINUTE=30', $d, freq=>'minutely', byminute=>[30]);

# 4 -- the snapshot: bymonth is deleted, but the later test still sees it, so
#      the BYDAY set is built as MONTHLY.  Correct answer, by accident.
show('4  YEARLY+BYMONTH+ordinal BYDAY (correct, via the snapshot)',
     'FREQ=YEARLY;BYMONTH=4;BYDAY=-1TH', $d,
     freq=>'yearly', bymonth=>[4], byday=>['-1th']);
