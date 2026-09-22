#!/usr/bin/env python3
"""Section 14.1.

Every core document of every corpus package, and of every converted CBZ,
must come back byte for byte from tools/canonical.py. The corpus is what an
implementer reads to learn what canonical means, so the corpus is what is
held to it.
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

import canonical                          # noqa: E402
from test_converter import convert        # noqa: E402

FIXTURES = ["manga.cbz", "bare.cbz", "messy.cbz"]

# Section 14.1 binds a conforming producer. A case built to break a rule about
# documents holds one no producer would have written — not well-formed, past a
# limit of section 13.1 — and has nothing to say about their layout.
NOT_CANONICAL = {"xml-not-well-formed", "xml-document-size-limit", "xml-nesting-limit"}
EXPECTED_PACKAGES = 67

CASES = [
    ("an element with no content is self-closing",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Reading xmlns="urn:koma:metadata" direction="rtl"/>\n'),
    ("text on several lines keeps its line breaks between the tags",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Descriptions xmlns="urn:koma:metadata">\n  <Description type="summary">Un.\n\nDeux.</Description>\n</Descriptions>\n'),
    ("normalized text stays on its element's line",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Titles xmlns="urn:koma:metadata">\n  <Title type="main">Le rivage</Title>\n</Titles>\n'),
    ("markup in text and attributes is escaped",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Titles xmlns="urn:koma:metadata">\n  <Title type="a&quot;b">&amp;&lt;&gt;</Title>\n</Titles>\n'),
    ("foreign content carries the declaration the root does not",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Extensions xmlns="urn:koma:metadata">\n  <shelf xmlns="urn:example:shelf" row="3"/>\n</Extensions>\n'),
    ("an element in no namespace says so",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Extensions xmlns="urn:koma:metadata">\n  <x xmlns=""/>\n</Extensions>\n'),
    ("a prefixed declaration is written under its prefix",
     b'<?xml version="1.0" encoding="UTF-8"?>\n<Metadata xmlns="urn:koma:metadata" xmlns:dc="http://purl.org/dc/elements/1.1/" version="0.9">\n  <Extensions>\n    <dc:rights>Libre</dc:rights>\n  </Extensions>\n</Metadata>\n'),
]


def documents(path):
    """The core documents of a package, and nothing else.

    Section 14.1 binds core documents. A carried-over ComicInfo.xml is never
    normative for KOMA (section 1) and is copied as it was found.
    """
    # A package that is no zip carries no core document, which is its own
    # case: L1-not-a-zip is a file, not an archive.
    try:
        with zipfile.ZipFile(path) as z:
            return {name: z.read(name) for name in z.namelist()
                    if name == "META-INF/container.xml" or (name.startswith("koma/") and name.endswith(".xml"))}
    except zipfile.BadZipFile:
        return {}


def check(label, raw, failures):
    root, prefixes = canonical.read(raw)
    written = canonical.serialize(root, prefixes)

    if written == raw:
        return failures

    print(f"FAIL     {label} is not canonical")
    print(f"         expected {raw[:200]!r}")
    print(f"         got      {written[:200]!r}")
    return failures + 1


def main():
    failures = 0

    for label, raw in CASES:
        failures = check(label, raw, failures)

    packages = sorted(f for f in os.listdir(os.path.join(ROOT, "corpus", "packages"))
                      if f.endswith(".koma"))
    assert len(packages) == EXPECTED_PACKAGES, (
        f"expected {EXPECTED_PACKAGES} packages, found {len(packages)}")

    with open(os.path.join(ROOT, "corpus", "expected.json"), encoding="utf-8") as fh:
        broken = {c["package"] for c in json.load(fh)["cases"] if c.get("code") in NOT_CANONICAL}

    for package in packages:
        if package in broken:
            continue

        for name, raw in documents(os.path.join(ROOT, "corpus", "packages", package)).items():
            failures = check(f"{package}: {name}", raw, failures)

    # The converter is an authoring tool, and section 14.1 binds it.
    with tempfile.TemporaryDirectory() as tmp:
        for fixture in FIXTURES:
            out = os.path.join(tmp, fixture.replace(".cbz", ".koma"))
            convert(os.path.join(ROOT, "examples", fixture), out, "--checksums")

            for name, raw in documents(out).items():
                failures = check(f"{fixture}: {name}", raw, failures)

    print(f"\n{'FAILED' if failures else 'PASSED'}: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
