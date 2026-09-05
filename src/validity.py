"""RFC 5545 3.3.10 rule-validity checks, independent of any expander.

Whether a rule is *valid* is a different question from whether DTSTART is
synchronized with it, and both are different from whether implementations
agree on its output. Implementations routinely accept rules the spec
prohibits; agreement on such a rule is not evidence of conformance.

Every check below quotes the sentence of RFC 5545 3.3.10 it enforces.
Text: https://www.rfc-editor.org/rfc/rfc5545.txt
sha256 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb
"""
import re

DAYS = ("SU", "MO", "TU", "WE", "TH", "FR", "SA")
_WEEKDAYNUM = re.compile(r"^([+-]?\d{1,2})?(SU|MO|TU|WE|TH|FR|SA)$")
ORDWK = (1, 53)  # RFC 5545 3.3.10 ABNF: ordwk = 1*2DIGIT ;1 to 53

# (id, quoted RFC sentence)
RULES = {
    "byday-numeric-freq": (
        "The BYDAY rule part MUST NOT be specified with a numeric value when "
        "the FREQ rule part is not set to MONTHLY or YEARLY."),
    "byday-numeric-byweekno": (
        "Furthermore, the BYDAY rule part MUST NOT be specified with a numeric "
        "value with the FREQ rule part set to YEARLY when the BYWEEKNO rule "
        "part is specified."),
    "bymonthday-weekly": (
        "The BYMONTHDAY rule part MUST NOT be specified when the FREQ rule "
        "part is set to WEEKLY."),
    "byyearday-freq": (
        "The BYYEARDAY rule part MUST NOT be specified when the FREQ rule part "
        "is set to DAILY, WEEKLY, or MONTHLY."),
    "byweekno-freq": (
        "This rule part MUST NOT be used when the FREQ rule part is set to "
        "anything other than YEARLY."),
    "bysetpos-needs-byxxx": (
        "It MUST only be used in conjunction with another BYxxx rule part."),
    "freq-required": (
        "The FREQ rule part ... MUST be specified in the recurrence rule."),
    "count-until-exclusive": (
        "The UNTIL or COUNT rule parts are OPTIONAL, but they MUST NOT occur "
        "in the same 'recur'."),
    "value-range": (
        "Valid values are as stated per rule part in RFC 5545 3.3.10."),
    "freq-value": (
        'freq = "SECONDLY" / "MINUTELY" / "HOURLY" / "DAILY" / "WEEKLY" '
        '/ "MONTHLY" / "YEARLY"'),
    "part-repeated": (
        "The other rule parts are OPTIONAL, but MUST NOT occur more than "
        "once."),
    "count-zero": (
        'COUNT = 1*DIGIT, and "The COUNT rule part defines the number of '
        'occurrences at which to range-bound the recurrence. The DTSTART '
        'property value always counts as the first occurrence." COUNT=0 is '
        "syntactically well-formed but cannot describe a recurrence whose "
        "first occurrence is DTSTART; flagged separately for that reason."),
}

FREQS = ("SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY",
         "YEARLY")

#: What `violations()` does *not* check. An empty result means "no violation
#: of the checks below was detected", never "this rule is valid".
NOT_CHECKED = (
    "BYSECOND/BYMINUTE/BYHOUR with a DATE-valued DTSTART (needs DTSTART)",
    "UNTIL value-type and UTC agreement with DTSTART (needs DTSTART)",
    "whether the rule is satisfiable at all (e.g. BYMONTHDAY=30;BYMONTH=2)",
    "whether DTSTART is synchronized with the rule (RFC 5545 3.8.5.3)",
    "RRULE-vs-RECUR framing: property parameters, folding, escaping",
)

RANGES = {  # part -> (lo, hi, allow_negative_mirror)
    "BYSECOND": (0, 60, False), "BYMINUTE": (0, 59, False),
    "BYHOUR": (0, 23, False), "BYMONTH": (1, 12, False),
    "BYMONTHDAY": (1, 31, True), "BYYEARDAY": (1, 366, True),
    "BYWEEKNO": (1, 53, True), "BYSETPOS": (1, 366, True),
}

BYXXX = ("BYSECOND", "BYMINUTE", "BYHOUR", "BYDAY", "BYMONTHDAY",
         "BYYEARDAY", "BYWEEKNO", "BYMONTH")


def parse(rule):
    """RRULE string -> {PART: raw value}. Raises ValueError on malformed input."""
    out = {}
    for chunk in rule.strip().split(";"):
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError("malformed rule part: %r" % chunk)
        k, v = chunk.split("=", 1)
        out[k.strip().upper()] = v.strip()
    return out


def _repeated(rule):
    seen, dup = set(), []
    for chunk in rule.strip().split(";"):
        if not chunk or "=" not in chunk:
            continue
        k = chunk.split("=", 1)[0].strip().upper()
        if k in seen:
            dup.append(k)
        seen.add(k)
    return dup


def _ints(raw):
    vals = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            raise ValueError("empty value")
        vals.append(int(tok))
    return vals


def violations(rule):
    """Return a list of {rule, part, detail, rfc} for a rule string.

    Empty list means no 3.3.10 violation was detected. It does not mean the
    rule is meaningful, satisfiable, or that DTSTART is synchronized with it.
    """
    p = parse(rule)
    out = []

    def bad(rid, part, detail):
        out.append({"rule": rid, "part": part, "detail": detail,
                    "rfc": RULES[rid]})

    freq = p.get("FREQ")
    if not freq:
        bad("freq-required", "FREQ", "FREQ is absent")
    elif freq.upper() not in FREQS:
        bad("freq-value", "FREQ", "%r is not one of %s" % (freq, ", ".join(FREQS)))

    for k in _repeated(rule):
        bad("part-repeated", k, "%s occurs more than once" % k)

    if "COUNT" in p and "UNTIL" in p:
        bad("count-until-exclusive", "COUNT/UNTIL", "both present")

    if "COUNT" in p:
        try:
            c = int(p["COUNT"])
        except ValueError:
            bad("value-range", "COUNT", "unparseable %r" % p["COUNT"])
        else:
            if c < 0:
                bad("value-range", "COUNT", "COUNT = 1*DIGIT, %d is negative" % c)
            elif c == 0:
                bad("count-zero", "COUNT", "COUNT=0")

    if "BYDAY" in p:
        numeric = []
        for tok in p["BYDAY"].split(","):
            m = _WEEKDAYNUM.match(tok.strip().upper())
            if not m:
                bad("value-range", "BYDAY", "unparseable weekdaynum %r" % tok)
                continue
            if m.group(1) is not None:
                n = abs(int(m.group(1)))
                if not (ORDWK[0] <= n <= ORDWK[1]):
                    bad("value-range", "BYDAY",
                        "ordwk %s out of range 1..53 in %r" % (m.group(1), tok.strip()))
                numeric.append(tok.strip())
        if numeric:
            if freq not in ("MONTHLY", "YEARLY"):
                bad("byday-numeric-freq", "BYDAY",
                    "numeric %s with FREQ=%s" % (numeric, freq))
            elif freq == "YEARLY" and "BYWEEKNO" in p:
                bad("byday-numeric-byweekno", "BYDAY",
                    "numeric %s with FREQ=YEARLY and BYWEEKNO=%s"
                    % (numeric, p["BYWEEKNO"]))

    if "BYMONTHDAY" in p and freq == "WEEKLY":
        bad("bymonthday-weekly", "BYMONTHDAY", "with FREQ=WEEKLY")
    if "BYYEARDAY" in p and freq in ("DAILY", "WEEKLY", "MONTHLY"):
        bad("byyearday-freq", "BYYEARDAY", "with FREQ=%s" % freq)
    if "BYWEEKNO" in p and freq != "YEARLY":
        bad("byweekno-freq", "BYWEEKNO", "with FREQ=%s" % freq)
    if "BYSETPOS" in p and not any(b in p for b in BYXXX):
        bad("bysetpos-needs-byxxx", "BYSETPOS", "no other BYxxx rule part")

    for part, (lo, hi, mirror) in RANGES.items():
        if part not in p:
            continue
        try:
            vals = _ints(p[part])
        except ValueError:
            bad("value-range", part, "unparseable %r" % p[part])
            continue
        for v in vals:
            ok = lo <= v <= hi or (mirror and -hi <= v <= -lo)
            if not ok:
                bad("value-range", part, "%d out of range" % v)

    if "INTERVAL" in p:
        try:
            if int(p["INTERVAL"]) < 1:
                bad("value-range", "INTERVAL", "%s < 1" % p["INTERVAL"])
        except ValueError:
            bad("value-range", "INTERVAL", "unparseable %r" % p["INTERVAL"])

    return out


def is_valid(rule):
    return not violations(rule)


if __name__ == "__main__":
    import sys, json
    for r in sys.argv[1:]:
        print(r, json.dumps(violations(r), indent=1))
