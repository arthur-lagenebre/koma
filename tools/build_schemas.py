#!/usr/bin/env python3
"""The RELAX NG XML form of the four schemas, generated from the compact form.

The compact syntax is what people read and edit. The XML syntax is what a
validator loads, and a language without a compact-syntax parser can load
nothing else, so both are committed. tests/test_schemas.py fails when an .rng
no longer matches the .rnc it was generated from: run this after editing one.
"""

import os
import sys

import rnc2rng

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS = os.path.join(ROOT, "schemas", "0.9")
NAMES = ("container", "metadata", "manifest", "navigation")


def rnc_path(name):
    return os.path.join(SCHEMAS, f"koma-{name}-0.9.rnc")


def rng_path(name):
    return os.path.join(SCHEMAS, f"koma-{name}-0.9.rng")


def generate(name):
    """The XML form of one schema, with the final LF the repository keeps."""
    with open(rnc_path(name), encoding="utf-8") as fh:
        return rnc2rng.dumps(rnc2rng.load(fh)).rstrip("\n") + "\n"


def main():
    for name in NAMES:
        with open(rng_path(name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(generate(name))
        print(f"wrote {os.path.relpath(rng_path(name), ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
