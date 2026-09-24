"""Is each derived corpus file still in exactly the form its generator writes?

`tools/verify_corpus.py` settles the real question -- does the corpus *re-derive*
-- but it costs a full rebuild, about thirty minutes, so it runs only in CI. That
gap is where finding 085 lived: finding 081 hand-edited two verdicts straight
into `corpus/disputed.json`, a *derived* file, and the edit appended a trailing
newline that `json.dump` never writes. One byte. CI went red on that push and
stayed red through three more, because nothing anyone types locally looked.

This is the cheap half, and it is deliberately a WEAKER claim: it does not
re-derive anything, so it cannot tell you the *content* is right. It only asks
whether the bytes on disk are what the generator's own `json.dump` call would
emit for the data they contain. That is enough to catch a hand edit, a reordered
key, a reindent, or an editor's trailing newline -- in seconds, before a push.

It is NOT a substitute for tools/verify_corpus.py. A file can be perfectly
canonical and completely wrong.

Run: python3 tests/test_corpus_canonical.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: corpus file -> (the generator that writes it, its json.dump kwargs, whether
#: that generator writes a trailing newline after the dump). Each entry must be
#: read off the generator's actual write call, not assumed: the five files
#: build_corpus.py derives end at the closing brace, datevalue_cases.py adds an
#: explicit f.write("\n"), and rfc_worked_examples.py neither passes sort_keys nor
#: adds a newline. The first draft of this table guessed that last flag and this
#: check is what caught it.
DERIVED = {
    "corroborated.json": ("src/build_corpus.py",
                          dict(indent=1, sort_keys=True), False),
    "disputed.json": ("src/build_corpus.py",
                      dict(indent=1, sort_keys=True), False),
    "coverage.json": ("src/build_corpus.py",
                      dict(indent=1, sort_keys=True), False),
    "grammar-coverage.json": ("src/build_corpus.py",
                              dict(indent=1, sort_keys=True), False),
    "pair-coverage.json": ("src/build_corpus.py",
                           dict(indent=1, sort_keys=True), False),
    "date-value-type.json": ("src/datevalue_cases.py",
                             dict(indent=1, sort_keys=True), True),
    "rfc5545-examples.json": ("src/rfc_worked_examples.py",
                              dict(indent=1), False),
}

#: Not derived, and so not checked here. Named rather than skipped by default,
#: so that a new corpus file has to be classified by a person instead of
#: quietly falling outside every check. adjudications.json is written by hand;
#: VERSION.json is written by tools/corpus_id.py and cannot hash itself.
NOT_DERIVED = {"adjudications.json", "VERSION.json", "SCHEMA.md"}

checks, fails = 0, []


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


corpus = os.path.join(ROOT, "corpus")

# A new file in corpus/ that nobody classified is a hole, not a pass.
present = set(os.listdir(corpus))
unclassified = sorted(present - set(DERIVED) - NOT_DERIVED)
check(not unclassified,
      "every file in corpus/ is classified derived or not (unclassified: %r)"
      % (unclassified,))
check(not (set(DERIVED) - present),
      "every file DERIVED names still exists (missing: %r)"
      % (sorted(set(DERIVED) - present),))

for name, (script, kw, newline) in sorted(DERIVED.items()):
    path = os.path.join(corpus, name)
    if not os.path.exists(path):
        continue
    raw = open(path, "rb").read()
    canon = json.dumps(json.load(open(path)), **kw).encode()
    if newline:
        canon += b"\n"
    check(raw == canon,
          "%s is byte-identical to what %s's json.dump writes "
          "(%d bytes on disk, %d canonical)"
          % (name, script, len(raw), len(canon)))

# The defect finding 085 found was a trailing byte, so say so separately: a
# length-only report would have read "85969 vs 85968" and told nobody which end.
for name, (_script, _kw, newline) in sorted(DERIVED.items()):
    path = os.path.join(corpus, name)
    if not os.path.exists(path):
        continue
    ends_nl = open(path, "rb").read()[-1:] == b"\n"
    check(ends_nl == newline,
          "%s %s a trailing newline, as its generator does"
          % (name, "ends with" if newline else "does not end with"))

print("%d checks, %d failed" % (checks, len(fails)))
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
