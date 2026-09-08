/*
 * Self-contained reproducer for: FREQ=WEEKLY with BYMONTH and BYSETPOS loses
 * (or shifts) occurrences in the week that straddles the BYMONTH boundary.
 *
 * Depends only on libical. No corpus, no harness, no scripts.
 *
 *   cc -o repro 019-weekly-bymonth-bysetpos.c \
 *      -I<prefix>/include -L<prefix>/lib -lical
 *   LD_LIBRARY_PATH=<prefix>/lib ./repro
 *
 * Every case below has a DTSTART that is the first instance of its own
 * recurrence set (RFC 5545 3.8.5.3 synchronization), so the recurrence set is
 * well defined.  Each case is expanded twice:
 *
 *   ITER  icalrecur_iterator_new/_next  -- the RRULE iterator directly
 *   COMP  icalcomponent_foreach_recurrence over a VEVENT holding the same
 *         DTSTART and RRULE -- the complete calendar-component recurrence set
 *
 * so that a discrepancy cannot be blamed on using the low-level iterator.
 */
#include <stdio.h>
#include <string.h>
#include <libical/ical.h>

struct case_t {
    const char *name;
    const char *dtstart;
    const char *rrule;
    int         want;          /* how many instances to print */
    const char *expected;      /* per RFC 5545 3.3.10 evaluation order */
};

static const struct case_t cases[] = {
{ "A  loss",
  "20260705T090000", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1", 8,
  "20260705 20260706 20260713 20260720 20260727 20270704 20270705 20270712" },

{ "B  shift",
  "20260712T090000", "FREQ=WEEKLY;BYMONTH=7;BYDAY=SU,TU;BYSETPOS=2", 8,
  "20260712 20260719 20260726 20270711 20270718 20270725 20280709 20280716" },

{ "C  skipped week after a gap",
  "20260802T090000", "FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU;BYSETPOS=-1", 8,
  "20260802 20260809 20260816 20260823 20260830 20270801 20270808 20270815" },

{ "D  control: single BYDAY",
  "20260705T090000", "FREQ=WEEKLY;BYDAY=SU;BYMONTH=7;BYSETPOS=1", 5,
  "20260705 20260712 20260719 20260726 20270704" },

{ "E  control: no BYSETPOS",
  "20260705T090000", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7", 6,
  "20260705 20260706 20260707 20260712 20260713 20260714" },
};

#define NCASES ((int)(sizeof cases / sizeof cases[0]))
#define MAXOUT 32

struct sink { char buf[MAXOUT * 10]; int n, want; };

static void emit(struct sink *s, struct icaltimetype t)
{
    if (s->n >= s->want)
        return;
    s->n++;
    snprintf(s->buf + strlen(s->buf), sizeof s->buf - strlen(s->buf),
             "%s%04d%02d%02d", s->n > 1 ? " " : "", t.year, t.month, t.day);
}

static void run_iter(const struct case_t *c, struct sink *s)
{
    struct icaltimetype dt = icaltime_from_string(c->dtstart);
    struct icalrecurrencetype *r = icalrecurrencetype_new_from_string(c->rrule);
    icalrecur_iterator *it = icalrecur_iterator_new(r, dt);
    struct icaltimetype t;

    for (t = icalrecur_iterator_next(it); !icaltime_is_null_time(t);
         t = icalrecur_iterator_next(it)) {
        emit(s, t);
        if (s->n >= s->want)
            break;
    }
    icalrecur_iterator_free(it);
    icalrecurrencetype_unref(r);
}

static void comp_cb(icalcomponent *comp, const struct icaltime_span *span, void *data)
{
    struct sink *s = data;
    (void)comp;
    emit(s, icaltime_from_timet_with_zone(span->start, 0, icaltimezone_get_utc_timezone()));
}

static void run_comp(const struct case_t *c, struct sink *s)
{
    char text[512];
    icalcomponent *comp;

    snprintf(text, sizeof text,
             "BEGIN:VEVENT\r\nUID:repro-%s\r\nDTSTAMP:20260101T000000Z\r\n"
             "DTSTART:%sZ\r\nRRULE:%s\r\nEND:VEVENT\r\n",
             c->name, c->dtstart, c->rrule);
    comp = icalcomponent_new_from_string(text);
    if (!comp) {
        snprintf(s->buf, sizeof s->buf, "(parse failed)");
        return;
    }
    icalcomponent_foreach_recurrence(comp,
        icaltime_from_string("20200101T000000Z"),
        icaltime_from_string("20300101T000000Z"), comp_cb, s);
    icalcomponent_free(comp);
}

int main(void)
{
    int i, bad = 0;

    printf("libical %s\n\n", ICAL_VERSION);

    for (i = 0; i < NCASES; i++) {
        const struct case_t *c = &cases[i];
        struct sink it = { {0}, 0, c->want }, cp = { {0}, 0, c->want };
        int ok_it, ok_cp;

        run_iter(c, &it);
        run_comp(c, &cp);
        ok_it = strcmp(it.buf, c->expected) == 0;
        ok_cp = strcmp(cp.buf, c->expected) == 0;
        if (!ok_it || !ok_cp)
            bad++;

        printf("== %s\n", c->name);
        printf("   DTSTART:%s\n   RRULE:%s\n", c->dtstart, c->rrule);
        printf("   expected  %s\n", c->expected);
        printf("   ITER   %s  %s\n", ok_it ? "ok  " : "DIFF", it.buf);
        printf("   COMP   %s  %s\n\n", ok_cp ? "ok  " : "DIFF", cp.buf);
    }
    printf("%d of %d cases differ from the expected set.\n", bad, NCASES);
    return bad != 0;
}
