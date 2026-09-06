"""Where rruleref's external inputs come from, in one place.

Until 2026-09-06 twenty call sites across ``src/`` and ``tests/`` hardcoded
absolute paths under ``/home/agent/terrarium/scratch``. The suite therefore ran
on exactly one machine, which quietly contradicted the point of the repository:
a reader is supposed to be able to re-run the adjudications rather than take my
word for them. This module is the fix. Every external input is resolved here,
each one overridable by an environment variable, each one with a failure
message that says how to obtain it.

Three inputs:

* **python-dateutil**, pinned to 2.9.0.post0. Pinned because several corpus
  cases record its *current* behaviour deliberately (see
  ``tests/test_date_value_type.py``); a different version changes what those
  tests mean.
* **The RFC text**, pinned by sha256. Every expected value in the corpus traces
  back to these bytes, so they are checked before anything parses them rather
  than trusted by filename.
* **rrule.js**, an optional third witness. Its absence must degrade, not crash:
  most of the suite does not need it.

``tools/bootstrap.sh`` provisions all three into ``vendor/``.
"""
import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(REPO, "vendor")

DATEUTIL_VERSION = "2.9.0.post0"

#: sha256 of the pinned specification text, as published by the RFC Editor.
RFC_SHA256 = {
    "5545": "c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb",
    "2445": "21bfccbb1f8d658d355b8e530feb2bf15d74e0bd3d988f1733569bce9eeaa828",
}

BOOTSTRAP = "run tools/bootstrap.sh from the repository root"


class MissingDependency(RuntimeError):
    """An input the suite cannot proceed without, with a way to get it."""


def _candidates(env_var, default):
    """Explicit override first, then the provisioned copy."""
    override = os.environ.get(env_var)
    return [override] if override else [default]


def add_dateutil_to_path():
    """Make ``dateutil`` importable, preferring a copy pinned for this repo.

    Returns the version string actually importable. A version other than the
    pin is a warning, not an error: it is legitimate to run the suite against
    a newer dateutil deliberately, and that is exactly how upstream drift is
    supposed to be discovered.
    """
    for path in _candidates("RRULEREF_PYLIBS", os.path.join(VENDOR, "pylibs")):
        if path and os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
            break
    try:
        # dateutil.rrule, not dateutil: the package imports without `six`,
        # and the module the whole suite depends on does not. Checking the
        # package alone let a copy missing `six` look present, and the tests
        # that need it degraded to a skip instead of a clear failure.
        import dateutil
        import dateutil.rrule  # noqa: F401
    except ImportError:
        raise MissingDependency(
            "python-dateutil %s is required and was not importable.\n"
            "Either %s, or set RRULEREF_PYLIBS to a directory containing it."
            % (DATEUTIL_VERSION, BOOTSTRAP)
        )
    version = getattr(dateutil, "__version__", "unknown")
    if version != DATEUTIL_VERSION:
        sys.stderr.write(
            "rruleref: warning: dateutil %s is importable, but the corpus was "
            "built against %s. Cases that pin current dateutil behaviour may "
            "legitimately fail.\n" % (version, DATEUTIL_VERSION)
        )
    return version


def rfc_path(number="5545", require=True):
    """Absolute path to the pinned RFC text, verified by sha256 before use.

    With ``require=False`` the resolved path is returned whether or not it
    exists and nothing is verified, so that it can serve as a default argument
    at import time. Anything that actually opens the file should pass it
    through :func:`check` first.
    """
    number = str(number)
    env_var = "RFC%s_TXT" % number
    default = os.path.join(VENDOR, "rfc%s.txt" % number)
    path = _candidates(env_var, default)[0]
    if os.path.isfile(path):
        _verify(path, number)
        return path
    if not require:
        return path
    raise MissingDependency(
        "RFC %s text not found at %s.\nEither %s, or set %s to a local copy."
        % (number, path, BOOTSTRAP, env_var)
    )


def check(path, number="5545"):
    """Validate a caller-supplied RFC path, then return it."""
    if not path or not os.path.isfile(path):
        return rfc_path(number)          # raises with the actionable message
    _verify(path, str(number))
    return path


_verified = set()


def _verify(path, number):
    if path in _verified:
        return
    want = RFC_SHA256[number]
    with open(path, "rb") as f:
        got = hashlib.sha256(f.read()).hexdigest()
    if got != want:
        raise MissingDependency(
            "RFC %s text at %s has sha256 %s, expected %s. Every expected "
            "value in the corpus is traced to the pinned bytes, so a "
            "different file cannot be used silently." % (number, path, got, want)
        )
    _verified.add(path)


def node_dir(required=False):
    """Directory to run rrule.js from, or ``None`` if it is not provisioned.

    Callers that can do useful work without the third witness should treat
    ``None`` as "skip the cross-check" rather than as an error.
    """
    for path in _candidates("RRULEREF_NODE_DIR", os.path.join(REPO, "js")):
        if path and os.path.isdir(os.path.join(path, "node_modules", "rrule")):
            return path
        candidate = path
    if required:
        raise MissingDependency(
            "rrule.js is not installed in %s.\nEither %s (it runs npm install "
            "there), or set RRULEREF_NODE_DIR." % (candidate, BOOTSTRAP)
        )
    return None
