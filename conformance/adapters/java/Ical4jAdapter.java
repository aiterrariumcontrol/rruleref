import net.fortuna.ical4j.model.Recur;
import org.json.simple.JSONObject;
import org.json.simple.JSONValue;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

/** Conformance adapter for ical4j. NDJSON in, NDJSON out. See conformance/PROTOCOL.md. */
public final class Ical4jAdapter {
    private static final DateTimeFormatter F = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss");

    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8)));
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) continue;
            JSONObject c = (JSONObject) JSONValue.parse(line);
            String id = (String) c.get("id");
            JSONObject o = new JSONObject();
            o.put("id", id);
            try {
                LocalDateTime seed = LocalDateTime.parse((String) c.get("dtstart"), F);
                int limit = (int) (long) (Long) c.get("limit");
                Recur<LocalDateTime> r = new Recur<>((String) c.get("rrule"));
                // Window end: DTSTART + the corpus's own 109500-day horizon
                // (corpus/SCHEMA.md), an adapter-imposed bound, recorded as such.
                // It cannot hide a disagreement with `expect`: no `expect` list in the
                // corpus runs past this horizon. It CAN hide an agreement with a rival
                // reading -- 21 of the corpus's `reading_alternatives` lists do run past
                // it, and on 7 cases this clip turns a match into a proper prefix.
                // score.py buckets those separately. Finding 057; do not widen this
                // window without reading it.
                LocalDateTime end = seed.plusDays(109500);
                List<LocalDateTime> ds = r.getDates(seed, seed, end, limit);
                org.json.simple.JSONArray a = new org.json.simple.JSONArray();
                for (LocalDateTime d : ds) a.add(d.format(F));
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
