// Finding 036 -- ical4j reads the host locale where RFC 5545 specifies WKST=MO.
//
// Needs ONLY ical4j and slf4j-api on the classpath. Nothing from this repository.
//
//   java -cp "conformance/adapters/java/libs/*" findings/repro/036-ical4j-locale-wkst.java
//
// Exits 0 if every claim below still holds, 1 otherwise.
//
// The locale is set from inside the process with Locale.setDefault() BEFORE the
// Recur is evaluated, so a single JVM run covers all three hosts. That is the
// same switch -Duser.language/-Duser.country flips; ByDayRule reads
// Locale.getDefault() when it is constructed, inside getDates().

import net.fortuna.ical4j.model.Recur;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class Repro {
    static final DateTimeFormatter F = DateTimeFormatter.ofPattern("yyyyMMdd");
    static int failed = 0;

    static List<String> dates(String rrule, String dtstart, int n, Locale loc) {
        Locale saved = Locale.getDefault();
        try {
            Locale.setDefault(loc);
            LocalDateTime seed = LocalDateTime.parse(dtstart,
                    DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss"));
            Recur<LocalDateTime> r = new Recur<>(rrule);
            List<String> out = new ArrayList<>();
            for (LocalDateTime d : r.getDates(seed, seed, seed.plusDays(10958), n)) {
                out.add(d.format(F));
            }
            return out;
        } finally {
            Locale.setDefault(saved);
        }
    }

    static void check(String label, boolean ok, String detail) {
        System.out.println((ok ? "  ok   " : "  FAIL ") + label + (detail.isEmpty() ? "" : "  " + detail));
        if (!ok) failed++;
    }

    public static void main(String[] args) {
        Locale SUN = Locale.US;               // week starts Sunday
        Locale MON = Locale.UK;               // week starts Monday
        Locale SAT = Locale.forLanguageTag("ar-EG");  // week starts Saturday

        System.out.println("ical4j version on classpath: " + versionOf());
        System.out.println();

        // ---- claim 1: an ordinary biweekly rule depends on the host locale ----
        String r1 = "FREQ=WEEKLY;INTERVAL=2;BYDAY=SU,TU";
        String d1 = "20260107T090000";   // a Wednesday; DTSTART is NOT an occurrence here,
                                         // but it is synchronized for the corpus cases below
        List<String> sun = dates(r1, d1, 6, SUN);
        List<String> mon = dates(r1, d1, 6, MON);
        System.out.println("1. " + r1 + "  DTSTART:" + d1);
        System.out.println("     Sunday-first host: " + sun);
        System.out.println("     Monday-first host: " + mon);
        check("the same rule gives different occurrences on the two hosts", !sun.equals(mon), "");

        // The Monday-first answer is what python-dateutil, dmfs lib-recur and
        // libical all produce (finding 036, measured separately).
        List<String> expected = Arrays.asList(
                "20260111", "20260120", "20260125", "20260203", "20260208", "20260217");
        check("Monday-first host matches the three-lineage answer", mon.equals(expected),
                mon.equals(expected) ? "" : "got " + mon);

        // ---- claim 2: WKST=MO removes the dependence ----
        List<String> sunW = dates(r1 + ";WKST=MO", d1, 6, SUN);
        List<String> satW = dates(r1 + ";WKST=MO", d1, 6, SAT);
        check("WKST=MO makes Sunday-first agree with the three-lineage answer",
                sunW.equals(expected), sunW.equals(expected) ? "" : "got " + sunW);
        check("WKST=MO makes Saturday-first agree too",
                satW.equals(expected), satW.equals(expected) ? "" : "got " + satW);

        // ---- claim 3: a corpus case whose DTSTART IS the first occurrence ----
        // RFC 5545 section 3.8.5.3's "undefined" escape does not apply to this one.
        String r3 = "FREQ=WEEKLY;INTERVAL=4;BYDAY=SU,TU";
        String d3 = "20260104T090000";   // 2026-01-04 is a Sunday: DTSTART is an occurrence
        List<String> s3 = dates(r3, d3, 6, SUN);
        List<String> m3 = dates(r3, d3, 6, MON);
        System.out.println();
        System.out.println("3. " + r3 + "  DTSTART:" + d3 + "   (DTSTART is a Sunday, so the");
        System.out.println("     rule and DTSTART are synchronized and the set is well defined)");
        System.out.println("     Sunday-first host: " + s3);
        System.out.println("     Monday-first host: " + m3);
        check("DTSTART is the first occurrence on the Monday-first host",
                !m3.isEmpty() && m3.get(0).equals("20260104"), "");
        check("a synchronized rule still depends on the host locale", !s3.equals(m3), "");

        // ---- claim 4: BYMONTH at YEARLY+BYWEEKNO is not a month filter, and duplicates ----
        String r4 = "FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52";
        String d4 = "20280101T090000";
        List<String> s4 = dates(r4, d4, 6, SUN);
        List<String> m4 = dates(r4, d4, 6, MON);
        List<String> t4 = dates(r4, d4, 6, SAT);
        System.out.println();
        System.out.println("4. " + r4 + "  DTSTART:" + d4);
        System.out.println("     Saturday-first host: " + t4);
        System.out.println("     Sunday-first   host: " + s4);
        System.out.println("     Monday-first   host: " + m4);
        boolean offMonth = s4.stream().anyMatch(x -> {
            int mm = Integer.parseInt(x.substring(4, 6));
            return mm != 1 && mm != 8;
        });
        check("emits dates outside BYMONTH=1,8", offMonth, "");
        check("emits duplicates", new HashSet<>(s4).size() < s4.size(), "");
        check("all three hosts disagree",
                !s4.equals(m4) && !s4.equals(t4) && !m4.equals(t4), "");

        System.out.println();
        if (failed == 0) {
            System.out.println("all claims hold");
        } else {
            System.out.println(failed + " claim(s) no longer hold -- finding 036 needs revisiting");
        }
        System.exit(failed == 0 ? 0 : 1);
    }

    static String versionOf() {
        try {
            String p = Recur.class.getProtectionDomain().getCodeSource().getLocation().getPath();
            return p.substring(p.lastIndexOf('/') + 1);
        } catch (Exception e) {
            return "unknown";
        }
    }
}
