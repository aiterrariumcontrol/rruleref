import org.dmfs.rfc5545.DateTime;
import org.dmfs.rfc5545.recur.RecurrenceRule;
import org.dmfs.rfc5545.recur.RecurrenceRuleIterator;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.JSONValue;

import java.io.*;

/** Conformance adapter for dmfs lib-recur. NDJSON in, NDJSON out. */
public final class DmfsAdapter {
    private static String fmt(DateTime d) {
        return String.format("%04d%02d%02dT%02d%02d%02d",
                d.getYear(), d.getMonth() + 1, d.getDayOfMonth(),
                d.getHours(), d.getMinutes(), d.getSeconds());
    }

    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(System.out)));
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) continue;
            JSONObject c = (JSONObject) JSONValue.parse(line);
            JSONObject o = new JSONObject();
            o.put("id", c.get("id"));
            try {
                DateTime seed = DateTime.parse((String) c.get("dtstart"));
                int limit = (int) (long) (Long) c.get("limit");
                RecurrenceRule r = new RecurrenceRule((String) c.get("rrule"),
                        RecurrenceRule.RfcMode.RFC5545_STRICT);
                RecurrenceRuleIterator it = r.iterator(seed);
                JSONArray a = new JSONArray();
                long horizon = seed.addDuration(new org.dmfs.rfc5545.Duration(1, 10958, 0)).getTimestamp();
                while (a.size() < limit && it.hasNext()) {
                    DateTime d = it.nextDateTime();
                    if (d.getTimestamp() > horizon) break;
                    a.add(fmt(d));
                }
                o.put("occurrences", a);
            } catch (Throwable t) {
                String m = t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage());
                o.put("error", m.length() > 200 ? m.substring(0, 200) : m);
            }
            out.println(o.toJSONString());
        }
        out.flush();
    }
}
