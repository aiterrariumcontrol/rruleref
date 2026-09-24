#!/usr/bin/perl
# Adapter for DateTime::Event::ICal (Perl, Flavio Soibelmann Glock, 2003).
# See ../../../PROTOCOL.md -- one JSON case per line on stdin, one JSON result
# per line on stdout.
#
# Everything in the corpus is floating local time. DateTime defaults to the
# floating time zone when none is given, which is exactly what is wanted here,
# so no timezone database can enter an answer.
#
# A case that never terminates is a result, not a crash: each one gets a hard
# wall-clock deadline via alarm() and is reported in the error column.
#
# Cases share one process. A fork-per-case variant was run as a control, in case
# a deadline unwinding out of the middle of a lazy DateTime::Set left later
# cases contaminated; it gave the identical pass/fail/other-reading split. See
# the README.
use strict;
use warnings;
use JSON::PP;
use DateTime;
use DateTime::Event::ICal;

my $DEADLINE = $ENV{RRULE_CASE_TIMEOUT} || 20;
my $json = JSON::PP->new->canonical;
# 'iterator' (default) or 'chain'; see findings/046.
my $ITER = $ENV{RRULE_DTICAL_ITER} || 'iterator';

# RRULE parts that take a list of integers.
my %INTLIST = map { $_ => 1 } qw(
    bysecond byminute byhour bymonthday byyearday byweekno bymonth bysetpos);

# Used for DTSTART and for UNTIL. PROTOCOL.md prescribes YYYYMMDDTHHMMSS for
# both, so a DATE-valued UNTIL is refused HERE and the library is never asked.
# That refusal is the harness's, not DateTime::Event::ICal's -- see finding 083.
sub parse_datetime {
    my ($s, $what) = @_;
    $what ||= 'dtstart';
    $s =~ /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$/
        or die "adapter refuses $what, not YYYYMMDDTHHMMSS: $s";
    return DateTime->new(year => $1, month => $2, day => $3,
                         hour => $4, minute => $5, second => $6);
}

sub parse_rrule {
    my ($s) = @_;
    my %args;
    for my $part (split /;/, $s) {
        my ($k, $v) = split /=/, $part, 2;
        next unless defined $v;
        $k = lc $k;
        if ($k eq 'freq') {
            $args{freq} = lc $v;
        } elsif ($k eq 'interval' || $k eq 'count') {
            $args{$k} = $v + 0;
        } elsif ($k eq 'until') {
            $args{until} = parse_datetime($v =~ s/Z$//r, 'until');
        } elsif ($k eq 'wkst') {
            $args{wkst} = lc $v;
        } elsif ($k eq 'byday') {
            # "1FR", "-1SU", "MO" -> the module wants them lowercased.
            $args{byday} = [ map { lc } split /,/, $v ];
        } elsif ($INTLIST{$k}) {
            $args{$k} = [ map { $_ + 0 } split /,/, $v ];
        } else {
            die "unsupported rule part: $k";
        }
    }
    die "no FREQ" unless exists $args{freq};
    return %args;
}

$| = 1;
while (my $line = <STDIN>) {
    $line =~ s/^\s+|\s+$//g;
    next if $line eq '';
    my $case = $json->decode($line);
    my ($id, $limit) = ($case->{id}, $case->{limit} + 0);
    my @occ;
    my $err;
    eval {
        local $SIG{ALRM} = sub { die "no answer within ${DEADLINE}s\n" };
        alarm $DEADLINE;
        my $dtstart = parse_datetime($case->{dtstart});
        my %args = parse_rrule($case->{rrule});
        my $set = DateTime::Event::ICal->recur(dtstart => $dtstart, %args);
        if ($ITER eq 'chain') {
            # Alternate traversal: repeated ->next instead of ->iterator. The two
            # disagree on some BYSETPOS sets; see findings/046. Not the default,
            # because ->iterator is the documented way to walk a DateTime::Set.
            my $dt = $set->next( $dtstart->clone->subtract( nanoseconds => 1 ) );
            while (@occ < $limit) {
                last unless defined $dt && !$dt->is_infinite;
                push @occ, $dt->strftime('%Y%m%dT%H%M%S');
                $dt = $set->next( $dt );
            }
        } else {
            my $it = $set->iterator;
            while (@occ < $limit) {
                my $dt = $it->next;
                last unless defined $dt;
                push @occ, $dt->strftime('%Y%m%dT%H%M%S');
            }
        }
        alarm 0;
        1;
    } or do {
        alarm 0;
        $err = $@ || 'unknown error';
        $err =~ s/\s+$//;
    };
    my $res = defined $err ? { id => $id, error => $err }
                           : { id => $id, occurrences => \@occ };
    print $json->encode($res), "\n";
}
