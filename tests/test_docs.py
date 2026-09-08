#!/usr/bin/env python3
"""Documentation counters.

README.md quotes how many mutations, pairing cases and corpus packages the
suites carry. Those numbers were wrong twice before this test existed: they
were written once and never followed the artifacts they describe. Nothing in
the specification or the workflow quotes a count any more, which is the right
choice, but it left these free to drift.

The test computes the real figures and asserts that the exact sentence
appears. Change a suite, and this fails until the prose catches up.

CHANGELOG.md deliberately carries no counts: a changelog entry is a historical
record and cannot be kept true by a test that only knows the present.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assert os.path.isdir(os.path.join(ROOT, "schemas")), (
    f"expected the repository root at {ROOT}; run these from tests/")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from spread_cases import CASES        # noqa: E402
from test_schemas import mutations    # noqa: E402


def real_counts():
    packages = json.load(open(os.path.join(ROOT, "corpus", "expected.json")))["cases"]
    return {"mutations": len(mutations()),
            "pairing": len(CASES),
            "packages": len(packages),
            "fixtures": len([f for f in os.listdir(os.path.join(ROOT, "examples"))
                             if f.endswith(".cbz")])}


def required_sentences(n):
    return {
        "README.md": [
            f"reject {n['mutations']} invalid",
            f"{n['pairing']} hand-written cases",
            f"{n['packages']} packages",
            f"{n['fixtures']} CBZ fixtures",
        ],
    }


def main():
    n = real_counts()
    failures = 0
    for filename, sentences in required_sentences(n).items():
        text = open(os.path.join(ROOT, filename), encoding="utf-8").read()
        for sentence in sentences:
            if sentence in text:
                print(f"ok       {filename} states {sentence!r}")
            else:
                failures += 1
                print(f"FAIL     {filename} does not state {sentence!r}")

    # A counter in the changelog cannot be kept true, so there must not be one.
    # Only a number immediately qualifying one of these nouns counts; a
    # section reference such as "section 10" is not a counter.
    changelog = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    live = re.compile(r"\b\d+\s+(?:\w+\s+)?"
                      r"(?:packages|pairing cases|mutations|fixtures)\b")
    # Text inside double quotes is a citation of past output, not a claim
    # about the present, so it cannot go stale and is exempt.
    quoted = re.compile(r'"[^"]*"')
    for line in changelog.splitlines():
        if live.search(quoted.sub("", line)):
            failures += 1
            print(f"FAIL     CHANGELOG.md carries a live counter: {line.strip()!r}")

    print(f"\n{'FAILED' if failures else 'PASSED'}: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
