#!/usr/bin/env python3
"""The CBZ converter.

Converts each example archive and asserts that the result is a conforming
package, that conversion is deterministic, and that page naming follows
section 8.1.1.
"""

import hashlib
import io
import os
import re
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assert os.path.isdir(os.path.join(ROOT, "schemas")), (
    f"expected the repository root at {ROOT}; run these from tests/")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import cbz_to_koma                        # noqa: E402
from check_corpus import check            # noqa: E402
from test_schemas import compile_schemas  # noqa: E402

FIXTURES = ["manga.cbz", "bare.cbz", "messy.cbz"]
ALLOWED_WARNINGS = {"no-publication-accessibility", "private-use-token",
                    "no-navigation-document"}


def convert(src, dst, *extra, quiet=True):
    """Returns whatever the converter printed on stderr."""
    argv = [src, dst, *(["--quiet"] if quiet else []), *extra]
    buf = io.StringIO()
    err, sys.stderr = sys.stderr, buf
    try:
        rc = cbz_to_koma.main(argv)
    finally:
        sys.stderr = err
    assert rc == 0, f"converter failed on {src}"
    return buf.getvalue()


def main():
    rng = compile_schemas()
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name in FIXTURES:
            src = os.path.join(ROOT, "examples", name)
            out = os.path.join(tmp, name.replace(".cbz", ".koma"))
            convert(src, out, "--checksums")

            errors, warnings = check(out, rng)
            unexpected = set(warnings) - ALLOWED_WARNINGS
            if errors or unexpected:
                failures += 1
                print(f"FAIL     {name}: errors={errors} unexpected={unexpected}")
            else:
                print(f"ok       {name} converts to a conforming package")

            # section 8.1.1: pages/NNN.ext, ascending, at least three digits,
            # widening with the page count.
            # Closed explicitly: on Windows an open handle blocks the
            # TemporaryDirectory cleanup and the suite exits non-zero long
            # after the assertions have passed.
            with zipfile.ZipFile(out) as z:
                pages = [n for n in z.namelist() if n.startswith("pages/")]
            width = max(3, len(str(len(pages))))
            expected = [f"pages/{i + 1:0{width}d}" for i in range(len(pages))]
            if [re.sub(r"\.[a-z]+$", "", p) for p in sorted(pages)] != expected:
                failures += 1
                print(f"FAIL     {name}: page naming departs from 8.1.1: {pages[:3]}")
            else:
                print(f"ok       {name} page naming follows 8.1.1")

            # The "never invents information" contract lives in the
            # assumption stream, so a test must actually read it. Renumbering
            # always happens; a direction guess happens only when ComicInfo
            # fails to state one, which manga.cbz does state.
            notes = convert(src, out + ".loud", "--checksums", quiet=False)
            required = ["pages renumbered"]
            if name != "manga.cbz":
                required.append("does not state a reading direction")
            missing = [r for r in required if r not in notes]
            if missing:
                failures += 1
                print(f"FAIL     {name}: undisclosed assumptions, missing {missing}")
            else:
                print(f"ok       {name} discloses its assumptions")

            twin = out + ".twin"
            convert(src, twin, "--checksums")
            h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h(out) != h(twin):
                failures += 1
                print(f"FAIL     {name}: conversion is not deterministic")
            else:
                print(f"ok       {name} converts deterministically")

        leaked = leaked_handles(tmp)
        if leaked:
            failures += 1
            print(f"FAIL     {len(leaked)} file handle(s) left open: {leaked[:3]}")
        else:
            print("ok       no file handles left open")

    print(f"\n{'FAILED' if failures else 'PASSED'}: {failures} failure(s)")
    return 1 if failures else 0


def leaked_handles(directory):
    """File descriptors still open inside `directory`.

    POSIX unlinks open files happily, so a leaked handle is invisible on Linux
    and fatal on Windows, where TemporaryDirectory cleanup raises
    PermissionError long after every assertion has passed. Reading /proc makes
    Linux fail for the same reason Windows does. Where /proc is absent the
    cleanup itself is the check.
    """
    fd_dir = "/proc/self/fd"
    if not os.path.isdir(fd_dir):
        return []
    leaked = []
    for entry in os.listdir(fd_dir):
        try:
            target = os.readlink(os.path.join(fd_dir, entry))
        except OSError:
            continue
        if target.startswith(os.path.realpath(directory) + os.sep):
            leaked.append(target)
    return leaked


if __name__ == "__main__":
    sys.exit(main())
