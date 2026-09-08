/*
 * Self-contained reproducer for: FREQ=YEARLY;BYWEEKNO=53 yields occurrences in
 * years that have only 52 ISO weeks, and those occurrences ignore BYDAY.
 *
 * Depends only on dmfs lib-recur (and its own runtime dependencies).
 * No corpus, no harness, no scripts.
 *
 *   mvn dependency:get -Dartifact=org.dmfs:lib-recur:0.17.1
 *   javac -cp '<libs>/*' -d out 016-lib-recur-byweekno-53.java
 *   java  -cp 'out:<libs>/*' Repro
 *
 * Every DTSTART below is itself the first instance of its own recurrence set,
 * so RFC 5545 3.8.5.3 synchronization holds and the recurrence set is defined.
 *
 * Expected values are NOT taken from another RRULE implementation.  They are
 * the ISO 8601 week-date calendar: the years in 2020..2060 that have a week 53
 * are 2020, 2026, 2032, 2037, 2043, 2048, 2054, 2060, and the Wednesday of
 * that week is obtained directly from the ISO week date (y, 53, 3).
 *
 * Prints one line per emitted instance, then a verdict per case.
 * Exit status: 0 if every case matched and every BYDAY invariant held,
 * otherwise 1.  (Read the printed FAIL lines for what differed.)
 */
import org.dmfs.rfc5545.DateTime;
import org.dmfs.rfc5545.recur.RecurrenceRule;
import org.dmfs.rfc5545.recur.RecurrenceRuleIterator;

import java.time.DayOfWeek;
import java.time.LocalDate;

class Repro {

    static final class Case {
        final String name, dtstart, rrule;
        final String[] expected;
        /** non-null => every instance must fall on this weekday (from BYDAY) */
        final DayOfWeek bydayInvariant;

        Case(String name, String dtstart, String rrule, DayOfWeek inv, String... expected) {
            this.name = name; this.dtstart = dtstart; this.rrule = rrule;
            this.bydayInvariant = inv; this.expected = expected;
        }
    }

    static final Case[] CASES = {
        new Case("A  week 53 with BYDAY=WE",
                 "20201230T090000", "FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE", DayOfWeek.WEDNESDAY,
                 "20201230T090000", "20261230T090000", "20321229T090000",
                 "20371230T090000", "20431230T090000", "20481230T090000"),

        // Control: same rule without BYDAY.  With no BYDAY the weekday comes
        // from DTSTART, which is a Wednesday, so the instances coincide.
        new Case("B  week 53, no BYDAY (control)",
                 "20201230T090000", "FREQ=YEARLY;BYWEEKNO=53", null,
                 "20201230T090000", "20261230T090000", "20321229T090000",
                 "20371230T090000", "20431230T090000", "20481230T090000"),

        // Control: week 52 exists in every ISO year, so this must not skip.
        new Case("C  week 52 with BYDAY=WE (control)",
                 "20201223T090000", "FREQ=YEARLY;BYWEEKNO=52;BYDAY=WE", DayOfWeek.WEDNESDAY,
                 "20201223T090000", "20211229T090000", "20221228T090000",
                 "20231227T090000", "20241225T090000", "20251224T090000"),
    };

    static String fmt(DateTime d) {
        return String.format("%04d%02d%02dT%02d%02d%02d",
                d.getYear(), d.getMonth() + 1, d.getDayOfMonth(),
                d.getHours(), d.getMinutes(), d.getSeconds());
    }

    static DayOfWeek weekdayOf(String stamp) {
        return LocalDate.of(Integer.parseInt(stamp.substring(0, 4)),
                            Integer.parseInt(stamp.substring(4, 6)),
                            Integer.parseInt(stamp.substring(6, 8))).getDayOfWeek();
    }

    public static void main(String[] args) throws Exception {
        // The jar carries no Implementation-Version, so print where the class
        // was actually loaded from rather than a version string that is null.
        System.out.println("lib-recur loaded from: "
                + RecurrenceRule.class.getProtectionDomain().getCodeSource().getLocation());
        int bad = 0;

        for (Case c : CASES) {
            System.out.println();
            System.out.println("== " + c.name);
            System.out.println("   DTSTART:" + c.dtstart);
            System.out.println("   RRULE:" + c.rrule);

            RecurrenceRule r = new RecurrenceRule(c.rrule, RecurrenceRule.RfcMode.RFC5545_STRICT);
            RecurrenceRuleIterator it = r.iterator(DateTime.parse(c.dtstart));

            String[] got = new String[c.expected.length];
            for (int i = 0; i < got.length && it.hasNext(); i++) got[i] = fmt(it.nextDateTime());

            boolean caseBad = false;
            for (int i = 0; i < got.length; i++) {
                String g = got[i], e = c.expected[i];
                String mark = e.equals(g) ? "   " : ">> ";
                if (!e.equals(g)) caseBad = true;
                String dow = g == null ? "" : "  (" + weekdayOf(g).toString().substring(0, 3) + ")";
                System.out.println("   " + mark + "got " + g + dow + "   want " + e);
            }

            // Spec-independent invariant: BYDAY is the last date part in the
            // 3.3.10 application order, so nothing can re-expand after it.
            // Whether it limited or expanded, every instance must be listed.
            if (c.bydayInvariant != null) {
                for (String g : got) {
                    if (g != null && weekdayOf(g) != c.bydayInvariant) {
                        System.out.println("   !! BYDAY VIOLATION: " + g + " is a "
                                + weekdayOf(g) + ", BYDAY names " + c.bydayInvariant);
                        caseBad = true;
                    }
                }
            }
            System.out.println("   " + (caseBad ? "FAIL" : "ok"));
            if (caseBad) bad++;
        }

        System.out.println();
        System.out.println(bad == 0 ? "all cases matched" : bad + " of " + CASES.length + " cases differ");
        System.exit(bad == 0 ? 0 : 1);
    }
}
