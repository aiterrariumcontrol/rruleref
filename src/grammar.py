"""RFC 5545 3.3.10's *other* printed coverage model: the RECUR ABNF.

src/coverage.py measures the corpus against the BYxxx/FREQ table -- a
*semantic* model, one cell per (rule part, frequency) interaction. It says
nothing about INTERVAL, WKST, COUNT, UNTIL, signs, or list arity, because the
table has no column for them. Those were named as unmeasured in the README's
honest limits.

3.3.10 prints a second model right above that table: the ABNF for the recur
value. This module takes *branch coverage of that grammar* as the second axis.
The feature set is not chosen by taste; it follows from three general rules
applied to the parsed grammar:

  * each alternative of an alternation is one feature;
  * each optional element `[x]` is two -- present and absent;
  * each repetition `*(x)` is two -- zero repeats and at least one.

Features are named by the path from `recur`, so the same production reached
two ways (`weekday` under BYDAY and under WKST) counts twice, which is the
point: WKST=MO and BYDAY=MO are not the same exercise.

The grammar is extracted from the pinned RFC text by program rather than
transcribed, for the reason src/coverage.py and src/vtimezone.py are: a
grammar retyped by hand is a grammar that can quietly disagree with the spec.

Leaves. Productions whose right-hand side is only a DIGIT repetition
(`seconds = 1*2DIGIT`) are treated as terminals: the 1-vs-2-digit branch is
lexical padding, not a distinction the spec draws anywhere. `date` and
`date-time` are defined in 3.3.4/3.3.5, outside this block, and are leaves
here; the UNTIL date/date-time choice is still measured, because that
alternation is inside `enddate`.

Text: https://www.rfc-editor.org/rfc/rfc5545.txt
sha256 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb
"""
import re, os

RFC = os.environ.get("RFC5545_TXT", "/home/agent/terrarium/scratch/rfc5545.txt")

START = "recur"


# --------------------------------------------------------------------------
# Extraction: pull the ABNF block for the RECUR value out of the RFC text.
# --------------------------------------------------------------------------

def _strip_comment(line):
    """Drop an ABNF comment, without cutting inside a quoted literal (`";"`)."""
    q = False
    for i, ch in enumerate(line):
        if ch == '"':
            q = not q
        elif ch == ";" and not q:
            return line[:i]
    return line


def _block(text):
    """The raw ABNF source lines defining `recur` .. `setposday`."""
    m = re.search(r"^ +recur +=", text, re.M)
    if not m:
        raise RuntimeError("recur ABNF not found in RFC text")
    end = re.search(r"^ +Description: ", text[m.start():], re.M)
    if not end:
        raise RuntimeError("end of recur ABNF not found")
    body = text[m.start():m.start() + end.start()]
    out = []
    for line in body.splitlines():
        # Drop page furniture and the prose comment lines (";" only lines).
        if re.match(r"^(Desruisseaux|RFC 5545 )", line.strip()):
            continue
        if re.match(r"^\s*\[Page \d+\]", line):
            continue
        s = _strip_comment(line).rstrip()
        if s.strip():
            out.append(s)
    return out


def source(path=RFC):
    """{rulename: right-hand-side text} in the order the RFC prints them."""
    rules, name, buf = {}, None, []
    for line in _block(open(path, encoding="utf-8", errors="replace").read()):
        m = re.match(r"^\s*([a-z][a-z0-9-]*)\s*=\s*(.*)$", line)
        if m:
            if name:
                rules[name] = " ".join(buf).strip()
            name, buf = m.group(1), [m.group(2)]
        elif name:
            buf.append(line.strip())
    if name:
        rules[name] = " ".join(buf).strip()
    return rules


# --------------------------------------------------------------------------
# A parser for the ABNF subset this block uses.
# Nodes: ('alt',[n]) ('seq',[n]) ('opt',n) ('rep',min,max,n) ('lit',s) ('ref',r)
# --------------------------------------------------------------------------

_TOK = re.compile(r'\s*(?:("(?:[^"]*)")|(\d*\*\d*)|(\d+)|([()\[\]/])|([A-Za-z][A-Za-z0-9-]*))')


def _lex(s):
    toks, i = [], 0
    while i < len(s):
        m = _TOK.match(s, i)
        if not m:
            if s[i].isspace():
                i += 1
                continue
            raise RuntimeError("cannot lex %r at %d" % (s, i))
        i = m.end()
        if m.group(1):
            toks.append(("lit", m.group(1)[1:-1]))
        elif m.group(2):
            lo, hi = m.group(2).split("*")
            toks.append(("rep", (int(lo) if lo else 0, int(hi) if hi else None)))
        elif m.group(3):
            toks.append(("num", int(m.group(3))))
        elif m.group(4):
            toks.append((m.group(4), None))
        else:
            toks.append(("name", m.group(5)))
    return toks


class _P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def alt(self):
        parts = [self.seq()]
        while self.peek()[0] == "/":
            self.take()
            parts.append(self.seq())
        return parts[0] if len(parts) == 1 else ("alt", parts)

    def seq(self):
        items = []
        while self.peek()[0] in ("lit", "name", "(", "[", "rep", "num"):
            items.append(self.item())
        if not items:
            raise RuntimeError("empty sequence")
        return items[0] if len(items) == 1 else ("seq", items)

    def item(self):
        kind, val = self.peek()
        if kind == "rep":
            self.take()
            return ("rep", val[0], val[1], self.item())
        if kind == "num":            # `1*2DIGIT` lexes as num,rep? no: handled above
            self.take()
            return ("lit", str(val))
        if kind == "lit":
            self.take()
            return ("lit", val)
        if kind == "name":
            self.take()
            return ("ref", val)
        if kind == "(":
            self.take()
            n = self.alt()
            assert self.take()[0] == ")"
            return n
        if kind == "[":
            self.take()
            n = self.alt()
            assert self.take()[0] == "]"
            return ("opt", n)
        raise RuntimeError("unexpected %r" % (kind,))


def grammar(path=RFC):
    """{rulename: AST}."""
    out = {}
    for name, rhs in source(path).items():
        out[name] = _P(_lex(rhs)).alt()
    return out


def _is_leaf_rule(node):
    """True for rules that are only a DIGIT repetition, e.g. `1*2DIGIT`."""
    return (node[0] == "rep" and node[3] == ("ref", "DIGIT"))


# --------------------------------------------------------------------------
# Feature enumeration: branch coverage of the extracted grammar.
#
# A feature id is  "<context>|<rule><path>|<choice>", where <context> is the
# enclosing recur-rule-part name (so `weekday` under BYDAY and under WKST are
# distinct obligations) and <path> is the child-index path within the rule, so
# ids are derived from the parsed tree rather than named by hand.
# --------------------------------------------------------------------------

# Defined in 3.3.4 and 3.3.5, outside this ABNF block. Matched, not expanded;
# the date / date-time choice itself is still a measured branch of `enddate`.
_LEAF_RE = {
    "DIGIT": r"[0-9]",
    "date": r"[0-9]{8}",
    "date-time": r"[0-9]{8}T[0-9]{6}Z?",
}


def _fid(ctx, rule, path, choice):
    return "%s|%s%s|%s" % (ctx or "recur", rule, path, choice)


def _children(node):
    if node[0] in ("alt", "seq"):
        return node[1]
    if node[0] == "opt":
        return [node[1]]
    if node[0] == "rep":
        return [node[3]]
    return []


def _branch_ctx(rule, node, i):
    """recur-rule-part's alternation is what sets the context."""
    if rule == "recur-rule-part" and node[0] == "alt":
        b = node[1][i]
        if b[0] == "seq" and b[1][0][0] == "lit":
            return b[1][0][1]
    return None


def _lit_label(node, i):
    b = node[1][i]
    if b[0] == "lit":
        return b[1]
    if b[0] == "seq" and b[1][0][0] == "lit":
        return b[1][0][1]
    if b[0] == "ref":
        return b[1]
    return str(i)


def features(path=RFC):
    """Every branch the grammar can take, in deterministic order."""
    g = grammar(path)
    out, seen = [], set()

    def add(f):
        if f not in seen:
            seen.add(f)
            out.append(f)

    def walk(node, rule, p, ctx):
        if node[0] == "alt":
            for i, b in enumerate(node[1]):
                add(_fid(ctx, rule, p, _lit_label(node, i)))
                walk(b, rule, p + "/%d" % i, _branch_ctx(rule, node, i) or ctx)
            return
        if node[0] == "opt":
            add(_fid(ctx, rule, p, "absent"))
            add(_fid(ctx, rule, p, "present"))
            walk(node[1], rule, p + "/0", ctx)
            return
        if node[0] == "rep":
            if _is_leaf_rule(node):
                return                      # `1*2DIGIT`: lexical, not a branch
            add(_fid(ctx, rule, p, "repeat=0"))
            add(_fid(ctx, rule, p, "repeat=1+"))
            walk(node[3], rule, p + "/0", ctx)
            return
        if node[0] == "seq":
            for i, b in enumerate(node[1]):
                walk(b, rule, p + "/%d" % i, ctx)
            return
        if node[0] == "ref" and node[1] in g and not _is_leaf_rule(g[node[1]]):
            walk(g[node[1]], node[1], "", ctx)
        return

    walk(g[START], START, "", None)
    return out


# --------------------------------------------------------------------------
# Matcher: parse an RRULE against the grammar, recording the branches taken.
# --------------------------------------------------------------------------

def _match(node, s, i, rule, p, ctx, g, taken):
    """Yield (end_index, taken_frozenset) for every parse of node at s[i:]."""
    k = node[0]
    if k == "lit":
        if s.startswith(node[1], i):
            yield i + len(node[1]), taken
        return
    if k == "ref":
        name = node[1]
        if name in _LEAF_RE:
            m = re.compile(_LEAF_RE[name]).match(s, i)
            if m:
                yield m.end(), taken
            return
        sub = g[name]
        if _is_leaf_rule(sub):
            m = re.compile(r"[0-9]{%d,%s}" % (sub[1], sub[2] or "")).match(s, i)
            if m:
                # longest first: numeric leaves are greedy but may need to give back
                for n in range(m.end(), i, -1):
                    yield n, taken
            return
        yield from _match(sub, s, i, name, "", ctx, g, taken)
        return
    if k == "alt":
        for idx, b in enumerate(node[1]):
            f = _fid(ctx, rule, p, _lit_label(node, idx))
            nctx = _branch_ctx(rule, node, idx) or ctx
            for e, t in _match(b, s, i, rule, p + "/%d" % idx, nctx, g,
                               taken | {f}):
                yield e, t
        return
    if k == "seq":
        def step(j, pos, t):
            if j == len(node[1]):
                yield pos, t
                return
            for e, t2 in _match(node[1][j], s, pos, rule, p + "/%d" % j, ctx,
                                g, t):
                yield from step(j + 1, e, t2)
        yield from step(0, i, taken)
        return
    if k == "opt":
        for e, t in _match(node[1], s, i, rule, p + "/0", ctx, g,
                           taken | {_fid(ctx, rule, p, "present")}):
            yield e, t
        yield i, taken | {_fid(ctx, rule, p, "absent")}
        return
    if k == "rep":
        lo, hi = node[1], node[2]
        leaf = _is_leaf_rule(node)

        def more(n, pos, t):
            if n >= lo and not (leaf and hi is not None and n > hi):
                if leaf:
                    yield pos, t
                else:
                    yield pos, t | {_fid(ctx, rule, p,
                                         "repeat=1+" if n else "repeat=0")}
            if hi is None or n < hi:
                for e, t2 in _match(node[3], s, pos, rule, p + "/0", ctx, g, t):
                    if e > pos:
                        yield from more(n + 1, e, t2)
        yield from more(0, i, taken)
        return
    raise RuntimeError("unknown node %r" % (k,))


def classify(rule, path=RFC, _cache={}):
    """The set of grammar branches a single RRULE string exercises.

    Raises ValueError if the string is not in the grammar -- which is itself
    useful: the corpus should not contain rules the RFC's own ABNF rejects.
    """
    g = _cache.get("g")
    if g is None:
        g = _cache["g"] = grammar(path)
    best = None
    for e, t in _match(g[START], rule, 0, START, "", None, g, frozenset()):
        if e == len(rule) and (best is None or len(t) < len(best)):
            best = t
    if best is None:
        raise ValueError("not a valid RECUR value per RFC 5545 3.3.10: %r" % rule)
    return set(best)
