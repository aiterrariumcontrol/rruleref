"""Assert every documented per-case deadline matches the adapter source that implements it.

`score.py` has no per-case deadline (standing rule 71), so every one of them
lives inside an adapter as a literal default in that adapter's own source. That
default decides which cases land in `error` rather than `fail`, and finding 047
measured how much it decides: over the same 1721 cases, 146 errors at 20 s
against 133 at 120 s. A deadline is therefore an *instrument parameter*, and a
document that misstates one invites a reader to re-run at a value that never
produced the published row and to read the difference as drift.

One did. `conformance/adapters/perl/README.md` said the `DateTime::Event::ICal`
adapter defaults to 10 seconds; the adapter has said `|| 20` since the line was
born. The sentence was copied from the `sabre/vobject` README, where 10 is
correct, and the number was not updated. Finding 073 -- whose whole subject is
which `error` cells are the clock and which are the library -- then took the
value from that README instead of from the source and published it in a table.
Finding 114.

What this checks:

  1. Each adapter's default is extracted from its source, and the pattern must
     match **exactly once**. An anchor that matches zero or twice is a failure,
     not a silent skip (standing rule 116).
  2. Every markdown line that names a deadline environment variable together
     with the word "default" must state that adapter's real default.
  3. Such a line must be attributable to exactly one adapter -- by naming the
     adapter's filename, or by living in that adapter's own directory. An
     unattributable claim fails, because a bare "default 10 s" is the shape the
     original error took.

  4. A line carrying no integer at all states no default *value* and is not a
     claim: prose about deadlines is not a claim about one. The defect shape
     always carries a number. LIMIT, stated because it is real: a default
     spelled out in words ("thirty seconds") escapes this checker.
  5. A line that merely *quotes* a false claim -- 114's record of the sentence
     it injected to prove this checker fires -- is exempted only by an entry in
     QUOTED_NON_CLAIMS carrying a checkable reason, keyed by the exact line
     text so that rewording it re-arms the check. Exemptions are printed, and
     an exemption that matches nothing is itself a failure.

Lines that set a deadline explicitly (`RRULE_CASE_TIMEOUT=300`) are not claims
about a default and are ignored.

    python3 tools/check_adapter_deadlines.py   # exit 1 on a mismatched claim
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ADAPTERS = os.path.join(REPO, "conformance", "adapters")

# source path -> (env var, regex with one capture group for the default literal)
SUBJECTS = {
    "perl/dtical_adapter.pl": (
        "RRULE_CASE_TIMEOUT",
        re.compile(r"\$ENV\{RRULE_CASE_TIMEOUT\}\s*\|\|\s*(\d+)"),
    ),
    "php/vobject_adapter.php": (
        "RRULE_CASE_TIMEOUT",
        re.compile(r"getenv\('RRULE_CASE_TIMEOUT'\)\s*\?:\s*(\d+)"),
    ),
    "icaljs_adapter.js": (
        "RRULE_CASE_TIMEOUT_MS",
        re.compile(r"process\.env\.RRULE_CASE_TIMEOUT_MS\)\s*\|\|\s*(\d+)"),
    ),
}

# ---------------------------------------------------------------------------
# Lines that are QUOTATIONS of a false claim rather than claims.
#
# This checker's first live catch was the finding that introduced it. Finding
# 114 proved the guard fires by injecting a bare "the default RRULE_CASE_TIMEOUT
# is 30 seconds" into the top-level README, and then recorded that injected
# sentence verbatim in its table of exercised failure modes. Grepping prose
# cannot tell a quoted wrong claim from a wrong claim, so the record of the
# guard working tripped the guard.
#
# Mirrors the CITATIONS dict in findings/repro/109-attribution-partition-audit.py:
# an exemption is a pair plus a reason a later reader can check, held in the
# tool rather than as a marker in the prose, so that the exemptions can be read
# in one place and counted.
#
# Keyed by (document, the exact stripped line) and NOT by line number: edits
# above it do not silently move the exemption, and rewording the sentence stops
# the exemption matching, so this fails closed. Every exemption taken is
# printed -- none is silent.
# ---------------------------------------------------------------------------
QUOTED_NON_CLAIMS = {
    ("findings/114-a-deadline-documented-from-a-sibling.md",
     '| added *"The default `RRULE_CASE_TIMEOUT` is 30 seconds"* to the '
     'top-level README | names no adapter, and is not in an adapter directory |'):
        "114 quotes the sentence it injected on purpose to make this checker "
        "fail; it is the record of the guard working, not a claim about any "
        "adapter. The finding says so in the same table: the right-hand column "
        "is what the checker printed.",
}

SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__"}
# "default 10 seconds", "default 10 s", "default 2000"
DEFAULT_WORD = re.compile(r"\bdefaults?\b", re.I)
INT = re.compile(r"(?<![\w.])(\d+)(?![\w.])")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def actual_defaults(problems):
    """Extract each adapter's real default, asserting each anchor matches once."""
    out = {}
    for rel, (env, pattern) in sorted(SUBJECTS.items()):
        path = os.path.join(ADAPTERS, rel)
        if not os.path.exists(path):
            problems.append("%s: adapter source is missing; the anchor cannot "
                            "be checked, so the docs cannot be trusted" % rel)
            continue
        hits = pattern.findall(read(path))
        if len(hits) != 1:
            problems.append(
                "%s: default-deadline anchor %s matched %d times, expected "
                "exactly 1 -- the adapter changed shape and this checker is "
                "now reading the wrong thing"
                % (rel, pattern.pattern, len(hits)))
            continue
        out[rel] = (env, int(hits[0]))
    return out


def markdown_files():
    for root, dirs, names in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(names):
            if name.endswith(".md"):
                yield os.path.join(root, name)


def attribute(rel_doc, line, defaults):
    """Which adapters could this claim be about? Filename, else enclosing dir."""
    named = [rel for rel in defaults if os.path.basename(rel) in line]
    if named:
        return named
    doc_dir = os.path.dirname(rel_doc)
    return [rel for rel in defaults
            if doc_dir == os.path.join("conformance", "adapters",
                                       os.path.dirname(rel)).rstrip("/")]


def main():
    problems = []
    defaults = actual_defaults(problems)
    envs = {env for env, _ in defaults.values()}
    # Longest first so RRULE_CASE_TIMEOUT does not swallow its _MS sibling.
    env_re = re.compile(r"\b(%s)\b" % "|".join(sorted(envs, key=len, reverse=True)))

    claims = 0
    quoted = []
    used = set()
    for path in markdown_files():
        rel_doc = os.path.relpath(path, REPO)
        for n, line in enumerate(read(path).splitlines(), 1):
            mentioned = set(env_re.findall(line))
            if not mentioned or not DEFAULT_WORD.search(line):
                continue
            # A line with no number on it states no default VALUE, so it
            # cannot be the defect: "defaults to 10 seconds" and the bare
            # "default 10 s" both carry one. Prose ABOUT deadlines -- including
            # this project's own writing about this checker -- does not.
            if not INT.search(line):
                continue
            key = (rel_doc, line.strip())
            if key in QUOTED_NON_CLAIMS:
                used.add(key)
                quoted.append("%s:%d is a quotation, not a claim: %s"
                              % (rel_doc, n, QUOTED_NON_CLAIMS[key]))
                continue
            candidates = [rel for rel in attribute(rel_doc, line, defaults)
                          if defaults[rel][0] in mentioned]
            where = "%s:%d" % (rel_doc, n)
            if not candidates:
                problems.append(
                    "%s: states a default deadline but names no adapter, and "
                    "does not live in an adapter directory -- say which "
                    "adapter it is about\n    %s" % (where, line.strip()))
                continue
            for rel in candidates:
                env, value = defaults[rel]
                claims += 1
                stated = [int(x) for x in INT.findall(line)]
                if value not in stated:
                    problems.append(
                        "%s: claims a default of %s for %s, but "
                        "conformance/adapters/%s defaults to %d\n    %s"
                        % (where, stated or "no number", env, rel, value,
                           line.strip()))

    for doc, text in sorted(set(QUOTED_NON_CLAIMS) - used):
        problems.append("the quoted-non-claim exemption for %s matches no line "
                        "any more -- the sentence was reworded or removed, so "
                        "delete the exemption\n    %s" % (doc, text))
    for q in quoted:
        print("note " + q)
    for p in problems:
        print("FAIL " + p)
    checked = ", ".join("%s=%d" % (os.path.basename(r), v)
                        for r, (_, v) in sorted(defaults.items()))
    print("%d documented default(s) checked against %d adapter source(s): %s"
          % (claims, len(defaults), checked))
    print("%d quoted non-claim(s) exempted, %d exemption(s) on file"
          % (len(quoted), len(QUOTED_NON_CLAIMS)))
    if problems:
        print("%d problem(s)" % len(problems))
        return 1
    print("every documented per-case deadline matches its adapter source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
