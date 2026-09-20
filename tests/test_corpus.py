#!/usr/bin/env python3
"""Section 15.1: the conformance corpus.

Checks the committed packages against expected.json, then rebuilds the corpus
in a temporary directory and checks the fresh packages too. The committed ones
are what third parties download; the rebuilt ones prove the generator still
agrees with them.

Byte equality between the two is deliberately not asserted: image encoders
differ between library versions, and a Pillow upgrade must not read as a
specification failure. Everything that is not an image is compared exactly,
so that a generator changed without regenerating the corpus is still caught.
"""

import json
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assert os.path.isdir(os.path.join(ROOT, "schemas")), (
    f"expected the repository root at {ROOT}; run these from tests/")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from check_corpus import check           # noqa: E402
from test_schemas import compile_schemas  # noqa: E402


EXPECTED_PACKAGES = 38


def run(directory, expected, rng, label):
    failures = 0
    for c in expected:
        path = os.path.join(directory, c["package"])
        if not os.path.exists(path):
            print(f"FAIL     {label}: {c['package']} missing")
            failures += 1
            continue
        errors, warnings = check(path, rng)
        want, code = c["outcome"], c["code"]
        if want == "valid":
            good = not errors
        elif want == "warning":
            good = not errors and code in warnings
        else:
            good = code in errors
        if good:
            print(f"ok       {label}: {c['package']}")
        else:
            failures += 1
            print(f"FAIL     {label}: {c['package']} "
                  f"wanted {want}/{code}, got errors={errors} warnings={warnings}")
    return failures


def structure(path):
    """Entry order, and the bytes of everything that is not an image.

    Entry order matters: 2.1 fixes mimetype as the first physical entry, and
    the central directory is not where that is decided. Images are compared by
    name only, since their bytes depend on the Pillow that produced them.
    """
    with zipfile.ZipFile(path) as z:
        names = [i.filename for i in z.infolist()]
        exact = {n: z.read(n) for n in names
                 if n == "mimetype" or n.endswith(".xml")}
    return names, exact


def compare(committed, rebuilt, expected):
    failures = 0
    for c in expected:
        name = c["package"]
        left = os.path.join(committed, name)
        right = os.path.join(rebuilt, name)
        if not (os.path.exists(left) and os.path.exists(right)):
            continue

        ln, lx = structure(left)
        rn, rx = structure(right)

        if ln != rn:
            print(f"FAIL     drift: {name} entry names or order differ")
            failures += 1
        elif lx != rx:
            differing = sorted(k for k in lx if lx.get(k) != rx.get(k))
            print(f"FAIL     drift: {name} differs in {', '.join(differing)}")
            failures += 1
        else:
            print(f"ok       no drift: {name}")
    return failures


def main():
    rng = compile_schemas()
    expected = json.load(open(os.path.join(ROOT, "corpus", "expected.json")))["cases"]
    if len(expected) != EXPECTED_PACKAGES:
        print(f"FAIL     expected {EXPECTED_PACKAGES} corpus packages, "
              f"found {len(expected)}")
        return 1

    failures = run(os.path.join(ROOT, "corpus", "packages"), expected, rng,
                   "committed")

    import build_corpus
    with tempfile.TemporaryDirectory() as tmp:
        build_corpus.build(tmp)
        fresh = json.load(open(os.path.join(tmp, "expected.json")))["cases"]
        if [c["package"] for c in fresh] != [c["package"] for c in expected]:
            print("FAIL     rebuilt corpus does not list the same packages")
            failures += 1
        failures += run(os.path.join(tmp, "packages"), fresh, rng, "rebuilt")
        failures += compare(os.path.join(ROOT, "corpus", "packages"),
                            os.path.join(tmp, "packages"), expected)

    print(f"\n{'FAILED' if failures else 'PASSED'}: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
