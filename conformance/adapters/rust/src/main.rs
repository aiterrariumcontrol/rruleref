use std::io::{self, BufRead, Write};
use rrule::RRuleSet;

#[derive(serde::Deserialize)]
struct Case {
    id: String,
    rrule: String,
    dtstart: String,
    limit: u16,
}

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = match line { Ok(l) => l, Err(_) => break };
        let line = line.trim();
        if line.is_empty() { continue; }
        let c: Case = match serde_json::from_str(line) {
            Ok(c) => c,
            Err(e) => { let _ = writeln!(out, "{{\"id\":\"\",\"error\":{}}}", json_str(&e.to_string())); continue; }
        };
        // Every case in the corpus is floating local time, and `rrule` requires
        // DTSTART and UNTIL to share a clock. Both are left floating -- the
        // crate's `Local` -- and the adapter is run under TZ=UTC so that
        // `Local` is a fixed-offset clock and no timezone database can enter
        // the answer. Forcing DTSTART to UTC instead makes the crate reject
        // every rule with a floating UNTIL, which measures the adapter.
        let input = format!("DTSTART:{}\nRRULE:{}", c.dtstart, c.rrule);
        match input.parse::<RRuleSet>() {
            Err(e) => {
                let _ = writeln!(out, "{{\"id\":{},\"error\":{}}}", json_str(&c.id), json_str(&e.to_string()));
            }
            Ok(set) => {
                let res = set.all(c.limit);
                let joined: Vec<String> = res.dates.iter()
                    .map(|d| json_str(&d.format("%Y%m%dT%H%M%S").to_string()))
                    .collect();
                let _ = writeln!(out, "{{\"id\":{},\"occurrences\":[{}]}}", json_str(&c.id), joined.join(","));
            }
        }
    }
    let _ = out.flush();
}

fn json_str(s: &str) -> String {
    serde_json::to_string(s).unwrap_or_else(|_| "\"\"".to_string())
}
