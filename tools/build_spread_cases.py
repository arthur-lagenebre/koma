#!/usr/bin/env python3
"""Export the pairing fixtures of tools/spread_cases.py as JSON.

The fixtures are the hand-written expectations of 10, and 5.0.1 asks for two
independent reading systems that agree. As Python source they can only be read
by a Python one, which makes the criterion harder to meet than it needs to be:
the package corpus is already language-neutral, .koma files and JSON, and this
puts the pairing cases on the same footing.

The file is generated, never edited. tests/test_spread.py regenerates it and
fails if the committed copy has drifted.

Usage:
    python tools/build_spread_cases.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spread_cases import CASES, spine   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "corpus", "spread-cases.json")


def document():
    return {
        "specification": "KOMA 0.9",
        "note": "Generated from tools/spread_cases.py. Expectations are written "
                "by hand from section 10 and are normative by example.",
        "cases": [
            {
                "id": c["id"],
                "note": c["note"],
                "direction": c["direction"],
                "spread": c["spread"],
                "viewport": c.get("viewport", True),
                "spine": spine(c["spine"]),
                "expected": c["expected"],
            }
            for c in CASES
        ],
    }


def main():
    text = json.dumps(document(), indent=2, ensure_ascii=False) + "\n"

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print(f"{len(CASES)} pairing cases written to {OUT}")


if __name__ == "__main__":
    main()
