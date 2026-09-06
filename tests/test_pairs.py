"""Checks for src/pairs.py.

The claim under test is "the corpus covers N of the M realizable pairs of
RECUR ABNF branches". A pairwise number is easy to make look good by declaring
the awkward pairs unrealizable, so almost everything here is aimed at the
denominator: every pair is accounted for, every realized pair really is
realized, and every rejection carries a reason traceable to the spec rather
than to this synthesizer.
"""
import sys, os, json, itertools
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import grammar
import pairs
import validity

FAIL = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


feats = grammar.features()
realized, unrealized = pairs.report()

check(len(pairs.all_pairs()) == len(feats) * (len(feats) - 1) // 2,
      "all_pairs is every unordered pair of the %d branches" % len(feats))
check(all(p == tuple(sorted(p)) for p in pairs.all_pairs()),
      "every pair is canonically ordered")
check(len(realized) + len(unrealized) == len(pairs.all_pairs()),
      "every pair is either realized or refused -- none dropped")
check(not (set(realized) & set(unrealized)), "no pair is both")

# The denominator. A pair refused for "not-co-synthesizable" is a hole in this
# module, not in the corpus, and would silently shrink the target.
check(not [p for p, w in unrealized.items() if w == "not-co-synthesizable"],
      "no pair is refused merely because _synth could not build it")

REASONS = {"no-common-freq", "needs-date-dtstart", "arity-conflict",
           "same-choice-point", "ungrammatical", "not-taken"}
unknown = sorted({w for w in unrealized.values()
                  if w not in REASONS and not w.startswith("invalid:")})
check(not unknown, "every refusal reason is one of the known kinds %s" % (unknown or ""))

# Every "invalid:" refusal names a MUST sentence validity.py quotes from 3.3.10.
ids = set()
for w in unrealized.values():
    if w.startswith("invalid:"):
        ids |= set(w[len("invalid:"):].split(","))
check(ids <= set(validity.RULES),
      "refusals cite validity.py rule ids: %s" % sorted(ids))

# Same-choice-point refusals really are two labels on one ABNF choice.
bad = [p for p, w in unrealized.items() if w == "same-choice-point"
       and pairs.choice_point(p[0]) != pairs.choice_point(p[1])]
check(not bad, "same-choice-point refusals share a choice point")

# The numerator. Each realized rule must actually be a rule.
bad = []
for p, (rule, ds) in realized.items():
    if validity.violations(rule):
        bad.append((p, rule, "invalid"))
        continue
    try:
        taken = grammar.classify(rule)
    except ValueError:
        bad.append((p, rule, "ungrammatical"))
        continue
    if not set(p) <= taken:
        bad.append((p, rule, "does not take the pair"))
check(not bad, "every realized pair's rule is valid, grammatical, and takes "
      "both branches (%d bad: %s)" % (len(bad), bad[:3]))

# A hand-worked pair, so the machinery is anchored to something readable.
rule, _ = pairs.build(("BYDAY|weekday|SU", "BYDAY|weekday|MO"))
check(set(rule.split(";")[1].split("=")[1].split(",")) == {"SU", "MO"},
      "two weekdays in one BYDAY list are realized as a list: %r" % rule)
check(("BYDAY|weekday|MO", "BYDAY|weekday|SU") in realized,
      "...and the pair is reported as realized, not as a gap")
check(pairs.build(("recur|recur/1|repeat=0", "FREQ|freq|YEARLY"))[0]
      == "FREQ=YEARLY",
      "the one-rule-part branch is realized by a rule with one part")

# Cross-checks against the built corpus, when it is present.
path = os.path.join(os.path.dirname(__file__), "..", "corpus", "pair-coverage.json")
if os.path.exists(path):
    pc = json.load(open(path))
    check(pc["meta"]["realizable"] == len(realized),
          "corpus/pair-coverage.json agrees on the realizable count (%d)"
          % pc["meta"]["realizable"])
    check(pc["meta"]["covered"] + pc["meta"]["uncovered"] == len(realized),
          "covered + uncovered = realizable")
    have = set()
    for f in ("corroborated.json", "disputed.json", "date-value-type.json"):
        fp = os.path.join(os.path.dirname(path), f)
        if os.path.exists(fp):
            for c in json.load(open(fp))["cases"]:
                have |= set(itertools.combinations(sorted(c["branches"]), 2))
    recomputed = sorted(p for p in realized if p not in have)
    check([list(p) for p in recomputed] == pc["uncovered"],
          "the uncovered list recomputes from the corpus's own branch lists")

print()
print("all checks passed" if not FAIL else "%d FAILED" % len(FAIL))
sys.exit(1 if FAIL else 0)
