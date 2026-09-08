#!/usr/bin/env python3
"""Section 10: the pairing algorithm.

Runs the reference implementation against the expectations in
tools/spread_cases.py. Those expectations are written by hand from the
specification. Never regenerate them from the implementation: doing so would
let a bug in the code silently become the definition of the format.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from koma_spread import paginate, PSEUDOCODE   # noqa: E402
from spread_cases import CASES, spine     # noqa: E402


EXPECTED_CASES = 15


SPEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "spec", "koma-0.9.md")


def spec_pseudocode():
    text = open(SPEC, encoding="utf-8").read()
    match = re.search(r"### 10\.4 Pairing algorithm.*?```text\n(.*?)```", text, re.S)
    if not match:
        return None
    return match.group(1)


def main():
    # Structural failures — the pseudocode check and the case count — are
    # tallied apart from case failures. Folding them together made the summary
    # announce "14/15 pairing cases" when all fifteen had passed and only the
    # pseudocode had drifted, sending the reader after a case that was fine.
    structural_failures = 0
    case_failures = 0

    # Section 10.4 says the pseudocode is what a reading system MUST follow,
    # so an implementation that merely agrees with the prose is not enough.
    block = spec_pseudocode()
    if block is None:
        print("FAIL     could not find the §10.4 pseudocode in the specification")
        structural_failures += 1
    elif block != PSEUDOCODE:
        structural_failures += 1
        print("FAIL     the §10.4 pseudocode and koma_spread.PSEUDOCODE differ")
        import difflib
        for line in list(difflib.unified_diff(
                PSEUDOCODE.splitlines(), block.splitlines(),
                "koma_spread.py", "specification", lineterm=""))[2:12]:
            print("        ", line)
    else:
        print("ok       §10.4 pseudocode matches the reference implementation")
    if len(CASES) != EXPECTED_CASES:
        print(f"FAIL     expected {EXPECTED_CASES} pairing cases, found {len(CASES)}")
        structural_failures += 1
    for c in CASES:
        got = paginate(spine(c["spine"]), c["direction"], c["spread"],
                       c.get("viewport", True))
        if got == c["expected"]:
            print(f"ok       {c['id']}")
        else:
            case_failures += 1
            print(f"FAIL     {c['id']}")
            print(f"         spine    {c['spine']}")
            print(f"         expected {c['expected']}")
            print(f"         got      {got}")
    failures = structural_failures + case_failures
    summary = f"{len(CASES) - case_failures}/{len(CASES)} pairing cases"
    if structural_failures:
        summary += f", {structural_failures} structural failure(s)"
    print(f"\n{'FAILED' if failures else 'PASSED'}: {summary}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
