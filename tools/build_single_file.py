#!/usr/bin/env python3
"""Build web/rrule-debugger.html: the debugger as one self-contained file.

The multi-file page under web/ needs a web server. Its modules are loaded with
`<script type="module" src=...>`, and a browser opening index.html from disk
refuses the cross-file imports, so the page renders its form and then silently
does nothing -- no results, no error. Anyone who downloads this repository and
double-clicks the page gets that.

This produces one HTML file with the CSS and the whole module graph inlined.
An inline module is never fetched, so it runs from a file:// URL. The file has
no server, no build step and no dependency, and it can be read end to end
before it is trusted with a calendar.

The bundler is deliberately small and refuses anything it does not fully
understand: the sources use only `import { a, b } from "./x.js"` and
`export const|let|function|class NAME`. If that ever stops being true this
exits non-zero rather than emitting a subtly broken file. tests/test_single_file.py
checks the built file is in sync with the sources.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
ENTRY = "app.js"
OUT = WEB / "rrule-debugger.html"

IMPORT_RE = re.compile(r'^import\s*\{([^}]*)\}\s*from\s*"([^"]+)"\s*;?\s*$', re.M | re.S)
EXPORT_RE = re.compile(r'^export\s+(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)', re.M)
# Anything else beginning with import/export is a form this bundler does not handle.
UNHANDLED_RE = re.compile(r'^\s*(?:export\s+(?!const|let|var|function|class)|import\s+(?!\{))', re.M)


def resolve(importer: str, spec: str) -> str:
    if not spec.startswith("."):
        sys.exit(f"{importer}: only relative specifiers are supported, got {spec!r}")
    return str((pathlib.PurePosixPath(importer).parent / spec).as_posix()).replace("./", "", 1)


def load(mod: str, seen: dict, order: list) -> None:
    """Depth-first load. `order` ends up in dependency order: a module is
    appended only after every module it imports from, so each __M[...] entry
    is already populated by the time a later one destructures it."""
    if mod in seen:
        return
    seen[mod] = None  # cycle marker
    src = (WEB / mod).read_text()
    if UNHANDLED_RE.search(src):
        sys.exit(f"{mod}: contains an import/export form this bundler does not handle")
    deps = []
    for names, spec in IMPORT_RE.findall(src):
        dep = resolve(mod, spec)
        deps.append((names, dep))
        load(dep, seen, order)
    if seen[mod] is not None:
        sys.exit(f"{mod}: import cycle")
    exports = EXPORT_RE.findall(src)
    if not exports and mod != ENTRY:
        sys.exit(f"{mod}: no exports found -- the export regex probably missed them")
    body = IMPORT_RE.sub(lambda m: f'const {{{m.group(1)}}} = __M[{resolve(mod, m.group(2))!r}];', src)
    body = re.sub(r'^export\s+', "", body, flags=re.M)
    seen[mod] = (body, exports)
    order.append(mod)


def build() -> str:
    mods: dict = {}
    order: list = []
    load(ENTRY, mods, order)
    chunks = ["const __M = {};"]
    for mod in order:
        body, exports = mods[mod]
        ret = "return {" + ", ".join(exports) + "};"
        chunks.append(f'// ---- {mod} ' + "-" * max(0, 66 - len(mod)) + f'\n__M[{mod!r}] = (() => {{\n{body}\n{ret}\n}})();')
    script = "\n\n".join(chunks)

    html = (WEB / "index.html").read_text()
    css = (WEB / "style.css").read_text()
    html, n = re.subn(r'<link[^>]*href="style\.css"[^>]*>', f"<style>\n{css}\n</style>", html)
    if n != 1:
        sys.exit(f"index.html: expected exactly one style.css link, found {n}")
    html, n = re.subn(r'<script[^>]*src="app\.js"[^>]*></script>',
                      lambda _: f'<script type="module">\n{script}\n</script>', html)
    if n != 1:
        sys.exit(f"index.html: expected exactly one app.js script tag, found {n}")
    note = ("<!-- Built by tools/build_single_file.py from the sources in web/. Do not edit by hand;\n"
            "     edit web/ and rebuild. https://github.com/aiterrariumcontrol/rruleref -->\n")
    return note + html


if __name__ == "__main__":
    out = build()
    if "--check" in sys.argv:
        cur = OUT.read_text() if OUT.exists() else ""
        if cur != out:
            sys.exit(f"{OUT.relative_to(ROOT)} is out of date -- run tools/build_single_file.py")
        print(f"{OUT.relative_to(ROOT)} is up to date ({len(out)} bytes)")
    else:
        OUT.write_text(out)
        print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} bytes)")
