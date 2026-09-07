/*
 * libical adapter for the rruleref conformance protocol.
 *
 * Reads one JSON object per line on stdin, writes one per line on stdout.
 * See conformance/PROTOCOL.md.
 *
 * The JSON reader here is deliberately narrow: it accepts exactly the shape
 * build_cases.py emits (four flat keys, no escapes, no nesting) and exits
 * non-zero on anything else, rather than guessing. A silently mis-parsed line
 * would score as a failure and look like a libical defect.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libical/ical.h>

#define MAXLINE 8192

static void die(const char *msg, const char *line)
{
    fprintf(stderr, "libical_adapter: %s in: %s\n", msg, line ? line : "(n/a)");
    exit(2);
}

/* Copy the string value of "key" into out. Returns 0 if the key is absent. */
static int json_str(const char *line, const char *key, char *out, size_t n)
{
    char pat[64];
    const char *p, *q;
    size_t len;

    snprintf(pat, sizeof pat, "\"%s\":", key);
    p = strstr(line, pat);
    if (!p)
        return 0;
    p += strlen(pat);
    while (*p == ' ')
        p++;
    if (*p != '"')
        die("expected a string value", line);
    p++;
    q = strchr(p, '"');
    if (!q)
        die("unterminated string", line);
    len = (size_t)(q - p);
    if (memchr(p, '\\', len))
        die("escape sequences are not supported", line);
    if (len >= n)
        die("value too long", line);
    memcpy(out, p, len);
    out[len] = '\0';
    return 1;
}

static long json_int(const char *line, const char *key)
{
    char pat[64];
    const char *p;
    char *end;
    long v;

    snprintf(pat, sizeof pat, "\"%s\":", key);
    p = strstr(line, pat);
    if (!p)
        die("missing integer key", line);
    p += strlen(pat);
    v = strtol(p, &end, 10);
    if (end == p)
        die("malformed integer", line);
    return v;
}

/* JSON string escaping for the error field: libical messages are plain ASCII,
   but a quote or backslash would produce invalid JSON, so escape both. */
static void print_json_string(const char *s)
{
    putchar('"');
    for (; *s; s++) {
        if (*s == '"' || *s == '\\')
            putchar('\\');
        if ((unsigned char)*s < 0x20)
            printf("\\u%04x", (unsigned char)*s);
        else
            putchar(*s);
    }
    putchar('"');
}

static void emit_error(const char *id, const char *msg)
{
    printf("{\"id\":\"%s\",\"error\":", id);
    print_json_string(msg);
    printf("}\n");
}

int main(void)
{
    char line[MAXLINE];

    icalerror_set_errors_are_fatal(0);

    while (fgets(line, sizeof line, stdin)) {
        char id[128], rrule[2048], dtstart[64];
        long limit;
#if ICAL_MAJOR_VERSION >= 4
        struct icalrecurrencetype *recur;
#else
        struct icalrecurrencetype recur;
#endif
        struct icaltimetype start, next;
        icalrecur_iterator *it;
        long emitted = 0;

        if (line[0] == '\n' || line[0] == '\0')
            continue;
        if (!json_str(line, "id", id, sizeof id))
            die("missing id", line);
        if (!json_str(line, "rrule", rrule, sizeof rrule))
            die("missing rrule", line);
        if (!json_str(line, "dtstart", dtstart, sizeof dtstart))
            die("missing dtstart", line);
        limit = json_int(line, "limit");

        icalerror_clear_errno();
        start = icaltime_from_string(dtstart);
        if (icaltime_is_null_time(start))
            die("unparseable dtstart", line);

        icalerror_clear_errno();
#if ICAL_MAJOR_VERSION >= 4
        recur = icalrecurrencetype_new_from_string(rrule);
        if (!recur || recur->freq == ICAL_NO_RECURRENCE) {
#else
        recur = icalrecurrencetype_from_string(rrule);
        if (recur.freq == ICAL_NO_RECURRENCE) {
#endif
            emit_error(id, icalerror_strerror(icalerrno));
            fflush(stdout);
            continue;
        }

        icalerror_clear_errno();
        it = icalrecur_iterator_new(recur, start);
        if (!it) {
            emit_error(id, icalerror_strerror(icalerrno));
            fflush(stdout);
            continue;
        }

        printf("{\"id\":\"%s\",\"occurrences\":[", id);
        while (emitted < limit) {
            next = icalrecur_iterator_next(it);
            if (icaltime_is_null_time(next))
                break;
            if (emitted)
                putchar(',');
            printf("\"%04d%02d%02dT%02d%02d%02d\"",
                   next.year, next.month, next.day,
                   next.hour, next.minute, next.second);
            emitted++;
        }
        printf("]}\n");
        fflush(stdout);
        icalrecur_iterator_free(it);
#if ICAL_MAJOR_VERSION >= 4
        icalrecurrencetype_unref(recur);
#endif
    }
    return 0;
}
