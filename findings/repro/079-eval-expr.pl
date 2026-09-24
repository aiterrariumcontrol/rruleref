#!/usr/bin/perl
# Evaluate the set-algebra expression that findings/repro/079-dtical-decompose.py
# CLAIMS DateTime::Event::ICal::recur() builds for a rule.
#
# This program deliberately does NOT load DateTime::Event::ICal.  It loads only
# DateTime::Event::Recurrence, the lower library recur() delegates to.  If its
# output matches the adapter's recorded output for a case, the case is
# attributed to the decomposition -- the defect is in how recur() rewrites the
# rule, not in how Recurrence expands one.  Where it does NOT match, the blame
# moves down into Recurrence.pm and has to be named separately.
#
# Same 20s alarm and same iterator walk as the adapter, so a difference cannot
# be an artefact of how the answer was read out.
use strict;
use warnings;
use JSON::PP;
use DateTime;
use DateTime::Set;
use DateTime::Span;
use DateTime::Event::Recurrence;

my $DEADLINE = $ENV{RRULE_CASE_TIMEOUT} || 20;
my $json = JSON::PP->new->canonical;

sub parse_dt {
    my ($s) = @_;
    $s =~ /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$/ or die "bad dt: $s";
    return DateTime->new(year=>$1, month=>$2, day=>$3,
                         hour=>$4, minute=>$5, second=>$6);
}

my $DTSTART;   # the handlers pass $dtstart as Recurrence's 'start', which is
               # what aligns INTERVAL>1 to DTSTART.  _recur_1fr does not.
sub build {
    my ($e) = @_;
    my $op = $e->{op};
    if ($op eq 'recurrence') {
        my %by;
        for my $k (keys %{$e->{args}}) {
            my $v = $e->{args}{$k};
            if ($k eq 'start') { $by{start} = $DTSTART->clone; next; }
            $by{$k} = (ref $v eq 'ARRAY') ? [ @$v ] : $v;
        }
        my $base = $e->{base};
        no strict 'refs';
        return DateTime::Event::Recurrence->$base(%by);
    }
    if ($op eq 'intersection') {
        my $s;
        for my $t (@{$e->{terms}}) {
            my $x = build($t);
            $s = defined $s ? $s->intersection($x) : $x;
        }
        return $s;
    }
    if ($op eq 'union') {
        my $s;
        for my $t (@{$e->{terms}}) {
            my $x = build($t);
            $s = defined $s ? $s->union($x) : $x;
        }
        return $s;
    }
    die "unhandled op $op";
}

$| = 1;
while (my $line = <STDIN>) {
    $line =~ s/^\s+|\s+$//g;
    next if $line eq '';
    my $c = $json->decode($line);
    my $e = $c->{expr};

    if ($e->{op} eq 'die') {
        print $json->encode({id=>$c->{id}, error=>$e->{msg}}), "\n";
        next;
    }
    if ($e->{op} ne 'span') {
        print $json->encode({id=>$c->{id}, skip=>'unexpected top op'}), "\n";
        next;
    }
    if ($e->{expr}{op} eq 'bysetpos') {
        print $json->encode({id=>$c->{id}, skip=>'bysetpos'}), "\n";
        next;
    }

    my @occ; my $err;
    eval {
        local $SIG{ALRM} = sub { die "no answer within ${DEADLINE}s\n" };
        alarm $DEADLINE;
        my $dtstart = parse_dt($c->{dtstart});
        $DTSTART = $dtstart;
        my $set = build($e->{expr});
        my $span = DateTime::Span->from_datetimes(start => $dtstart);
        if (defined $e->{until}) {
            $span = $span->complement(
                DateTime::Span->from_datetimes(after => parse_dt($e->{until})));
        }
        $set = $set->intersection($span);
        my $limit = $c->{limit} + 0;
        $limit = $e->{count} if defined $e->{count} && $e->{count} < $limit;
        my $it = $set->iterator;
        while (@occ < $limit) {
            my $dt = $it->next;
            last unless defined $dt;
            push @occ, $dt->strftime('%Y%m%dT%H%M%S');
        }
        alarm 0;
        1;
    } or do {
        alarm 0;
        $err = $@ || 'unknown error';
        $err =~ s/\s+$//;
    };
    print $json->encode(defined $err ? {id=>$c->{id}, error=>$err}
                                     : {id=>$c->{id}, occurrences=>\@occ}), "\n";
}
