// Finding 037 -- at FREQ=WEEKLY, ical4j applies the BYMONTH limit to the period
// seed rather than to the expanded occurrences.
//
// Needs ONLY ical4j and slf4j-api on the classpath. Nothing from this repository.
//
//   java -cp "conformance/adapters/java/libs/*" findings/repro/037-ical4j-weekly-bymonth.java
//
// Exits 0 if every claim below still holds, 1 otherwise.
//
// The locale is pinned to en-GB from inside the process so that WKST defaults to
// MO, which is what RFC 5545 3.3.10 specifies. That holds finding 036's separate
// locale defect still, so what is measured here is only this one.

import net.fortuna.ical4j.model.Recur;
import java.time.DayOfWeek;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;
import java.util.*;

public class Repro {
    static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyyMMdd");
    static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss");
    static int failed = 0;

    static List<String> ical4j(String rrule, String dtstart, int n) {
        Locale saved = Locale.getDefault();
        try {
            Locale.setDefault(Locale.UK);   // WKST defaults to MO
            LocalDateTime seed = LocalDateTime.parse(dtstart, STAMP);
            Recur<LocalDateTime> r = new Recur<>(rrule);
            List<String> out = new ArrayList<>();
            for (LocalDateTime d : r.getDates(seed, seed, seed.plusDays(10958), n)) out.add(d.format(DAY));
            return out;
        } finally {
            Locale.setDefault(saved);
        }
    }

    // The two readings, as models. Plain weekday BYDAY only; no BYSETPOS.
    static List<String> model(String rrule, String dtstart, int n, boolean seedLimited) {
        Map<String, String> p = new LinkedHashMap<>();
        for (String part : rrule.split(";")) {
            String[] kv = part.split("=", 2);
            p.put(kv[0], kv[1]);
        }
        int interval = Integer.parseInt(p.getOrDefault("INTERVAL", "1"));
        DayOfWeek wkst = day(p.getOrDefault("WKST", "MO"));
        Set<Integer> months = new HashSet<>();
        for (String m : p.get("BYMONTH").split(",")) months.add(Integer.parseInt(m));
        List<DayOfWeek> byday = new ArrayList<>();
        for (String d : p.get("BYDAY").split(",")) byday.add(day(d));

        LocalDateTime start = LocalDateTime.parse(dtstart, STAMP);
        LocalDateTime seed = start;
        List<String> out = new ArrayList<>();
        for (int guard = 0; guard < 20000 && out.size() < n; guard++) {
            if (!seedLimited || months.contains(seed.getMonthValue())) {
                LocalDateTime ws = seed.with(TemporalAdjusters.previousOrSame(wkst));
                List<LocalDateTime> cands = new ArrayList<>();
                for (DayOfWeek d : byday) {
                    cands.add(ws.plusDays(Math.floorMod(d.getValue() - wkst.getValue(), 7)));
                }
                Collections.sort(cands);
                for (LocalDateTime c : cands) {
                    if (!seedLimited && !months.contains(c.getMonthValue())) continue;
                    if (!c.isBefore(start) && out.size() < n) out.add(c.format(DAY));
                }
            }
            seed = seed.plusWeeks(interval);
        }
        return out;
    }

    static DayOfWeek day(String s) {
        switch (s) {
            case "MO": return DayOfWeek.MONDAY;
            case "TU": return DayOfWeek.TUESDAY;
            case "WE": return DayOfWeek.WEDNESDAY;
            case "TH": return DayOfWeek.THURSDAY;
            case "FR": return DayOfWeek.FRIDAY;
            case "SA": return DayOfWeek.SATURDAY;
            default:   return DayOfWeek.SUNDAY;
        }
    }

    static void check(String claim, boolean ok) {
        System.out.printf("%-4s %s%n", ok ? "ok" : "FAIL", claim);
        if (!ok) failed++;
    }

    public static void main(String[] args) {
        System.out.println("ical4j " + Recur.class.getPackage().getImplementationVersion()
                + "  (locale pinned to en-GB, so WKST defaults to MO)\n");

        // ---- Case A: a February-only rule that emits a March date.
        // DTSTART 2024-02-29 is a Thursday, TH is in BYDAY and the month is 2,
        // so DTSTART is synchronized and RFC 5545 3.8.5.3 does not apply.
        String ruleA = "FREQ=WEEKLY;BYMONTH=2;BYDAY=FR,TH,WE";
        String dtA = "20240229T090000";
        List<String> a = ical4j(ruleA, dtA, 12);
        System.out.println(ruleA + "  DTSTART:" + dtA);
        System.out.println("  " + a + "\n");

        check("A1 emits 20240301, a March date, though BYMONTH=2",
                a.contains("20240301"));
        check("A2 it is the only emitted date outside February",
                a.stream().filter(d -> !d.substring(4, 6).equals("02")).count() == 1);
        check("A3 the spurious March date costs the window one February date",
                a.stream().filter(d -> d.substring(4, 6).equals("02")).count()
                        == model(ruleA, dtA, 12, false).stream().filter(d -> d.substring(4, 6).equals("02")).count() - 1);
        check("A4 the correct reading emits only February dates",
                model(ruleA, dtA, 12, false).stream().allMatch(d -> d.substring(4, 6).equals("02")));

        // ---- Case B: a valid in-month occurrence dropped.
        String ruleB = "FREQ=WEEKLY;BYDAY=MO,SU;BYMONTH=4";
        String dtB = "20270404T090000";
        List<String> b = ical4j(ruleB, dtB, 8);
        System.out.println(ruleB + "  DTSTART:" + dtB);
        System.out.println("  " + b + "\n");

        check("B1 drops 20270426, the last April Monday",
                !b.contains("20270426"));
        check("B2 and reaches into March instead, emitting 20280327",
                b.contains("20280327"));
        check("B3 the correct reading keeps 20270426",
                model(ruleB, dtB, 8, false).contains("20270426"));

        // ---- The models, against the library, on both cases.
        boolean seedMatches = ical4j(ruleA, dtA, 12).equals(model(ruleA, dtA, 12, true))
                && ical4j(ruleB, dtB, 8).equals(model(ruleB, dtB, 8, true));
        check("C1 ical4j matches the SEED-LIMITED model exactly on both cases", seedMatches);

        boolean corrDiffers = !model(ruleA, dtA, 12, false).equals(model(ruleA, dtA, 12, true))
                && !model(ruleB, dtB, 8, false).equals(model(ruleB, dtB, 8, true));
        check("C2 the two models genuinely disagree on both cases", corrDiffers);

        // ---- Single-day BYDAY is unaffected: the seed IS the candidate.
        List<String> single = ical4j("FREQ=WEEKLY;BYDAY=MO;BYMONTH=4", "20270405T090000", 6);
        check("D1 single-day BYDAY on DTSTART's weekday keeps 20270426 and stays in April",
                single.contains("20270426") && single.stream().allMatch(d -> d.substring(4, 6).equals("04")));

        System.out.println(failed == 0
                ? "\nAll claims hold."
                : "\n" + failed + " claim(s) no longer hold.");
        System.exit(failed == 0 ? 0 : 1);
    }
}
