"""034 -- When did RFC 5545 section 3.3.10's expand/limit table arrive, and was
the sentence it collides with touched when it did?

Finding 024 showed that two sentences of RFC 5545 section 3.3.10 give different
answers for FREQ=YEARLY;BYMONTHDAY=15 and FREQ=YEARLY;BYWEEKNO=20, that five
real implementations split along exactly that line, and that the section never
says which wins. This script establishes the drafting history of the two texts
across all thirteen published documents in the line:

    RFC 2445 (Nov 1998)
    draft-ietf-calsify-rfc2445bis-00 .. -10 (Oct 2005 .. Apr 2009)
    RFC 5545 (Sep 2009)

For each document it records, from the text itself:

  * whether the DTSTART-fill sentence is present, and its exact wording;
  * whether the expand/limit table is present;
  * whether the sentence that introduces the table is present;
  * the YEARLY column of the table, when there is one.

The drafts are fetched from the IETF archive on first run and cached under
vendor/calsify-bis/. Every file, including the two RFCs, is checked against a
pinned sha256 before it is read: this finding is entirely a claim about what
these documents say, so an unpinned copy would make it unfalsifiable.

    python3 findings/repro/034-table-provenance.py --out findings/data/034-table-provenance.json

Exits non-zero if any pinned hash is wrong or any expectation below fails.
"""
import argparse, hashlib, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
import env  # noqa: E402

CACHE = os.path.join(REPO, "vendor", "calsify-bis")
URL = "https://www.ietf.org/archive/id/draft-ietf-calsify-rfc2445bis-%s.txt"

#: sha256 of each draft as served by the IETF archive, 2026-09-13.
DRAFT_SHA256 = {
    "00": "146f7f59e1d1c293ac31e0e6af5b20c73d72bf905e1fc03e1e80a0f5b675e838",
    "01": "54620f7f65b7fc0ac73f2958d6ef0243ece2dcb000b2853881dc3930abe192e4",
    "02": "2fd0b15543889697ebe0f91dd205d22fb236b89fba831a6e667a14a32ec6dc31",
    "03": "7d04baecc9903501a9eee8236c1df813e646e4e94d1bb1de64d0b705898466db",
    "04": "db6fb2a6a1c9c7eeb153728f39cd2e775fc93e02abdfc77fe58e3679bf05a191",
    "05": "317fad730db65fea5f800ad323a2312429d542719e959c985cb4dd8a7dac35d6",
    "06": "5dbd070e4c53811ec7c5263d16790c3d3ecae3199fa3eca0d253434b55e84586",
    "07": "435eeebaf83c5ead756fbb8ae3220037fb1a066035a2663c6935b25450f2deec",
    "08": "32f3499f79cc42a0e72bd755360c943188720379641d080c0d030f2a0f903c42",
    "09": "cef72373c59ed8b4e8f1a9953987e39a2f23b47a2f0422d3b59903c834b91558",
    "10": "02020440640cd692c45e1e4830b35bca14f810b4704b655b973ccd28a348532e",
}

# Page furniture in an RFC/I-D text file: the form feed, the running header and
# footer, and the "[Page n]" line. All of it can fall in the middle of the
# sentences being compared, so it is removed before any matching.
FURNITURE = re.compile(
    r"^(\x0c|Internet-Draft\s|RFC \d+\s+iCalendar|"
    r"[A-Z][A-Za-z&. ]+\s+(Standards Track|Expires)\s.*\[Page \d+\]|"
    r".*\[Page \d+\]\s*)", re.M)

FILL = re.compile(
    r"Similarly, if the BYMINUTE.{0,200}?would have been retrieved from the "
    r'"?DTSTART"? property\.', re.S)
INTRO = re.compile(
    r"The table below summarizes the dependency of BYxxx rule part expand or "
    r"limit behaviou?r on the FREQ rule part value\.")
ROW = re.compile(r"\|(BY[A-Z]+)\s*\|([^|]*\|){6}([^|]*)\|")
# The change-log item that says why the table was added. Each draft's log is
# cumulative -- -08 still carries the "Changes in -07" section -- so the item
# appears in every draft from the one that introduced it onwards, and the
# check below is that the first draft carrying the item is the first draft
# carrying the table. The RFC Editor removes the log, so RFC 5545 has none.
CHANGELOG = re.compile(r"[a-z]\.\s+(Issue \d+: Added a table[^.]*\.)")


def flatten(text):
    """One line, no page furniture, single-spaced -- comparable across files."""
    return " ".join(FURNITURE.sub("", text).split())


def read(path, want_sha):
    with open(path, "rb") as handle:
        raw = handle.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != want_sha:
        sys.exit("%s has sha256 %s, expected %s" % (path, got, want_sha))
    return raw.decode("utf-8", "replace")


def draft(number):
    path = os.path.join(CACHE, "draft-ietf-calsify-rfc2445bis-%s.txt" % number)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        sys.stderr.write("fetching %s\n" % (URL % number))
        with urllib.request.urlopen(URL % number, timeout=60) as response:
            body = response.read()
        with open(path, "wb") as handle:
            handle.write(body)
    return read(path, DRAFT_SHA256[number])


def yearly_column(flat):
    """The YEARLY cell of every BYxxx row, in table order, or None."""
    if not ROW.search(flat):
        return None
    return {m.group(1): m.group(3).strip() for m in ROW.finditer(flat)}


def survey(name, text):
    flat = flatten(text)
    fill = FILL.search(flat)
    changelog = CHANGELOG.search(flat)
    return {
        "document": name,
        "fill_sentence": fill.group(0) if fill else None,
        "table_intro": bool(INTRO.search(flat)),
        "table_yearly_column": yearly_column(flat),
        "change_log_item": changelog.group(1) if changelog else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    documents = [("RFC 2445", read(env.rfc_path("2445"), env.RFC_SHA256["2445"]))]
    documents += [("draft-%s" % n, draft(n)) for n in sorted(DRAFT_SHA256)]
    documents += [("RFC 5545", read(env.rfc_path("5545"), env.RFC_SHA256["5545"]))]

    rows = [survey(name, text) for name, text in documents]

    # The wording of the fill sentence, as a set of distinct strings.
    wordings = sorted({r["fill_sentence"] for r in rows})
    with_table = [r["document"] for r in rows if r["table_yearly_column"]]

    problems = []
    if any(r["fill_sentence"] is None for r in rows):
        problems.append("the fill sentence is missing from at least one document")
    expected_table = ["draft-07", "draft-08", "draft-09", "draft-10", "RFC 5545"]
    if with_table != expected_table:
        problems.append("table present in %s, expected %s" % (with_table, expected_table))
    if len(wordings) != 2:
        problems.append("expected exactly 2 wordings of the fill sentence, got %d"
                        % len(wordings))
    logs = [r["document"] for r in rows if r["change_log_item"]]
    if not logs or logs[0] != with_table[0]:
        problems.append("the 'Added a table' change-log item first appears in "
                        "%s, but the table first appears in %s"
                        % (logs[0] if logs else "no document", with_table[0]))
    columns = {json.dumps(r["table_yearly_column"], sort_keys=True)
               for r in rows if r["table_yearly_column"]}
    if len(columns) != 1:
        problems.append("the YEARLY column is not identical in all %d documents "
                        "that have the table" % len(with_table))

    result = {
        "documents": rows,
        "fill_sentence_wordings": wordings,
        "documents_with_table": with_table,
        "table_added_by": next((r["change_log_item"] for r in rows
                                if r["change_log_item"]), None),
        "problems": problems,
    }
    text = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text + "\n")
    else:
        print(text)

    for row in rows:
        print("%-10s fill=%s table=%s intro=%s"
              % (row["document"], "yes" if row["fill_sentence"] else "NO",
                 "yes" if row["table_yearly_column"] else "no ",
                 "yes" if row["table_intro"] else "no "), file=sys.stderr)
    print("%d distinct wordings of the fill sentence across %d documents"
          % (len(wordings), len(rows)), file=sys.stderr)
    if problems:
        sys.exit("FAILED: " + "; ".join(problems))
    print("ok", file=sys.stderr)


if __name__ == "__main__":
    main()
