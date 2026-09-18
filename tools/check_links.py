#!/usr/bin/env python3
"""Resolve every relative Markdown link in README.md, RESULTS.md and findings/.

Two broken links shipped in published findings before this existed (a filename
finding 051 never had, and ../PROTOCOL.md when PROTOCOL.md lives under
conformance/). Run it after adding or renaming anything under findings/.

Links of the form [rule N](../README.md) are a pre-existing convention across
several findings: the README does not enumerate the rules, so the target file
resolves but the anchor means nothing. That is left alone and not reported.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def targets():
    yield 'README.md'
    yield 'conformance/RESULTS.md'
    yield 'conformance/PROTOCOL.md'
    for d in ('findings',):
        for name in sorted(os.listdir(os.path.join(ROOT, d))):
            if name.endswith('.md'):
                yield os.path.join(d, name)


def main():
    broken = []
    missing = []
    checked = 0
    for rel in targets():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            # A named target that has moved must fail, not vanish: the first
            # version of this tool listed RESULTS.md, which lives under
            # conformance/, and silently checked nothing in it.
            missing.append(rel)
            continue
        base = os.path.dirname(path)
        with open(path) as fh:
            text = fh.read()
        for m in LINK.finditer(text):
            href = m.group(1)
            if href.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            file_part = href.split('#', 1)[0]
            if not file_part:
                continue
            checked += 1
            if not os.path.exists(os.path.normpath(os.path.join(base, file_part))):
                broken.append((rel, href))
    print('%d relative links checked, %d broken' % (checked, len(broken)))
    for rel, href in broken:
        print('  %s -> %s' % (rel, href))
    for rel in missing:
        print('  MISSING TARGET FILE: %s' % rel)
    return 1 if (broken or missing) else 0


if __name__ == '__main__':
    sys.exit(main())
