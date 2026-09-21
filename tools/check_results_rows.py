"""Assert every scored row published in RESULTS.md accounts for the whole case set.

Every row of a scoring table partitions the same 1727 cases into disjoint
buckets, so its numeric cells must sum to the case count. That is a weak
invariant -- a row can sum correctly and still be stale -- but it is free, and
it is the one that has actually caught errors here twice: the `ical4j` row of
the main table summed to 1726 (fixed at finding 075), and the JVM-locale table
published three rows summing to 1659, 1658 and 1658 against a 1727-case corpus
(finding 077).

Rows are opted in with an HTML comment immediately above the table:

    <!-- rowsum: total=cases cols=pass:4,fail:5,other:6,prefix:7,error:8 -->
    <!-- rowsum: skip reason="not a partition of the case set" -->

`total=cases` means the live count in cases.ndjson, so the check tightens
automatically when the corpus moves instead of freezing yesterday's number.
`cols` names each bucket and its 1-based column index. Indices are given
explicitly because other cells carry integers too -- a release year in a
lineage cell would otherwise be summed as a bucket.

    python3 tools/check_results_rows.py   # exit 1 on a bad or unmarked row

This does not verify that a row is a *current* measurement; only `cases_id`
does that, and only for rows that carry one. See finding 077 for why a table
without an identifier beside it is the thing to distrust.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PAGE = os.path.join(REPO, "conformance", "RESULTS.md")
CASES = os.path.join(REPO, "conformance", "cases.ndjson")

CELL = re.compile(r"(?<![\w.`-])(\d+)(?![\w.%])")
DIRECTIVE = re.compile(r"<!--\s*rowsum:\s*(.*?)\s*-->")


def case_count():
    with open(CASES) as fh:
        return sum(1 for line in fh if line.strip())


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def cell_int(cell):
    """The integer in one markdown cell, or None.

    Footnote markers and symbols share the cell with the number, so the number
    is extracted from the cell rather than the cell parsed as a number.
    """
    found = CELL.findall(cell)
    return int(found[0]) if len(found) == 1 else None


def tables(lines):
    """Yield (directive, header_lineno, [(lineno, rowtext), ...]) per table."""
    i, pending = 0, None
    while i < len(lines):
        m = DIRECTIVE.search(lines[i])
        if m:
            pending, i = (m.group(1), i + 1), i + 1
            continue
        if lines[i].lstrip().startswith("|"):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            body = [(n + 1, lines[n]) for n in range(start + 2, i)]
            yield pending, start + 1, body
            pending = None
            continue
        if lines[i].strip():
            pending = None
        i += 1


def main():
    total = case_count()
    lines = open(PAGE).read().splitlines()
    bad, checked, unmarked = [], 0, []
    for directive, header_ln, body in tables(lines):
        if directive is None:
            unmarked.append(header_ln)
            continue
        spec = directive[0]
        if spec.startswith("skip"):
            continue
        opts = dict(re.findall(r"(\w+)=(\S+)", spec))
        want = total if opts.get("total") == "cases" else int(opts["total"])
        cols = [(n, int(i)) for n, i in
                (c.split(":") for c in opts["cols"].split(","))]
        for ln, row in body:
            row_cells = cells(row)
            picked, missing = [], []
            for name, idx in cols:
                v = cell_int(row_cells[idx - 1]) if idx <= len(row_cells) else None
                (picked if v is not None else missing).append(
                    v if v is not None else name)
            if missing:
                bad.append((ln, "no single integer in column(s) %s"
                            % ", ".join(missing)))
                continue
            checked += 1
            if sum(picked) != want:
                bad.append((ln, "%s = %s sum to %d, not %d"
                            % ("+".join(n for n, _ in cols),
                               "+".join(map(str, picked)), sum(picked), want)))
    for ln, why in bad:
        print("RESULTS.md:%d: %s" % (ln, why))
        print("    %s" % lines[ln - 1].strip())
    print("%d rows checked against %d cases, %d bad, %d tables unmarked"
          % (checked, total, len(bad), len(unmarked)))
    if unmarked:
        print("unmarked tables at lines: %s" % ", ".join(str(n) for n in unmarked))
        print("every table must carry a rowsum directive or an explicit skip;"
              " an unmarked table is how the JVM-locale table escaped for nine"
              " days (finding 077)")
    return 1 if (bad or unmarked) else 0


if __name__ == "__main__":
    sys.exit(main())
