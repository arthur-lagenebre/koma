#!/usr/bin/env python3
"""Layer 2: the four RELAX NG schemas.

Compiles each schema, validates the reference instances, then applies a
mutation per case and asserts that the schema rejects it. A schema that
accepts everything passes no test, so the rejection half matters more than
the acceptance half.
"""

import os
import sys

import rnc2rng
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assert os.path.isdir(os.path.join(ROOT, "schemas")), (
    f"expected the repository root at {ROOT}; run these from tests/")
SCHEMAS = os.path.join(ROOT, "schemas", "0.9")
EXAMPLES = os.path.join(SCHEMAS, "examples")
NS = {"md": "urn:koma:metadata", "mf": "urn:koma:manifest",
      "nv": "urn:koma:navigation"}


def compile_schemas(outdir=None):
    out = {}
    for name in ("container", "metadata", "manifest", "navigation"):
        rnc = os.path.join(SCHEMAS, f"koma-{name}-0.9.rnc")
        rng_text = rnc2rng.dumps(rnc2rng.load(open(rnc)))
        if outdir:
            with open(os.path.join(outdir, f"koma-{name}-0.9.rng"), "w") as f:
                f.write(rng_text)
        out[name] = etree.RelaxNG(etree.fromstring(rng_text.encode()))
    return out


def mutations():
    """(label, schema name, instance file, mutation) tuples."""
    def m(label, schema, inst, fn):
        return (label, schema, inst, fn)

    return [
        m("Reading/@direction=ttb", "metadata", "metadata.xml",
          lambda r: r.find("md:Reading", NS).set("direction", "ttb")),
        m("Contributor/@type=group", "metadata", "metadata.xml",
          lambda r: r.find("md:Contributors/md:Contributor", NS).set("type", "group")),
        m("Item/@media-type=image/gif", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("media-type", "image/gif")),
        m("Checksum/@algorithm=md5", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item/mf:Checksum", NS).set("algorithm", "md5")),
        m("PageTarget/@spread-position=center", "navigation", "nav.xml",
          lambda r: r.find("nv:PageList/nv:PageTarget", NS).set("spread-position", "center")),
        m("background-color=#FFF", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item[2]", NS).set("background-color", "#FFF")),
        m("width with a leading zero", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("width", "016")),
        m("decorative=1", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item/mf:Accessibility", NS).set("decorative", "1")),
        m("roles in uppercase", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item[2]", NS).set("roles", "Story")),
        m("roles with a space", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item[2]", NS).set("roles", "story; recap")),
        m("Region/@x out of range", "navigation", "nav.xml",
          lambda r: r.find("nv:Regions/nv:RegionSequence/nv:Region", NS).set("x", "1.5")),
        m("href escaping the package", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("href", "../secrets/x.jpg")),
        m("absolute href", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("href", "/pages/001.jpg")),
        m("version=1.0 in a 0.9 document", "manifest", "manifest.xml",
          lambda r: r.set("version", "1.0")),
        m("Reading absent", "metadata", "metadata.xml",
          lambda r: r.remove(r.find("md:Reading", NS))),
        m("Titles out of canonical order", "metadata", "metadata.xml",
          lambda r: (lambda t: (r.remove(t), r.append(t)))(r.find("md:Titles", NS))),
        m("core element inside Extensions", "metadata", "metadata.xml",
          lambda r: etree.SubElement(r.find("md:Extensions", NS),
                                     "{urn:koma:metadata}Whatever")),
        m("unknown core element", "metadata", "metadata.xml",
          lambda r: etree.SubElement(r, "{urn:koma:manifest}Spine")),
        m("navigation with no section", "navigation", "nav.xml",
          lambda r: [r.remove(c) for c in list(r)]),
        m("TOC entry without Label", "navigation", "nav.xml",
          lambda r: (lambda e: e.remove(e.find("nv:Label", NS)))
                    (r.find("nv:TableOfContents/nv:Entry", NS))),
        m("Collection without Name", "metadata", "metadata.xml",
          lambda r: (lambda c: c.remove(c.find("md:Name", NS)))
                    (r.find("md:Collections/md:Collection", NS))),
        m("Resolution/@unit=lpi", "metadata", "metadata.xml",
          lambda r: r.find("md:Provenance/md:Digitization/md:Resolution", NS)
                     .set("unit", "lpi")),

        # Added after the first external review. Each of these was accepted
        # before the schemas were tightened; see the review findings named.
        m("G3 whitespace-only Identifier", "metadata", "metadata.xml",
          lambda r: setattr(r.find("md:Identifiers/md:Identifier", NS), "text", "   ")),
        m("G4 href containing a percent sign", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("href", "pages/%41.jpg")),
        m("G4 href containing a query", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("href", "pages/a.jpg?x=1")),
        m("G4 href containing a fragment", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item", NS).set("href", "pages/a.jpg#f")),
        m("G5 relative Link/@href", "metadata", "metadata.xml",
          lambda r: r.find("md:Links/md:Link", NS).set("href", "../inside/package")),
        m("G6 Subject with neither text nor code", "metadata", "metadata.xml",
          lambda r: etree.SubElement(r.find("md:Subjects", NS),
                                     "{urn:koma:metadata}Subject")),
        m("G6 Subject/@code without @scheme", "metadata", "metadata.xml",
          lambda r: etree.SubElement(r.find("md:Subjects", NS),
                                     "{urn:koma:metadata}Subject", code="X")),
        m("G7 decorative=true with AlternativeText", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item/mf:Accessibility", NS)
                     .set("decorative", "true")),
        m("G8 core element nested deep inside an extension", "metadata", "metadata.xml",
          lambda r: etree.SubElement(r.find("md:Extensions", NS)[0],
                                     "{urn:koma:metadata}Sneaky")),
        m("C1 Decimal01 without its leading zero", "navigation", "nav.xml",
          lambda r: r.find("nv:Regions/nv:RegionSequence/nv:Region", NS).set("x", ".5")),
        m("C2 private-use token of 64 characters", "manifest", "manifest.xml",
          lambda r: r.find("mf:Resources/mf:Item[2]", NS)
                     .set("roles", "x-" + "a" * 62)),
    ]


EXPECTED_MUTATIONS = 33
EXPECTED_INSTANCES = 4


def main():
    rng = compile_schemas()
    failures = 0

    # A shrinking suite must not pass green.
    if len(mutations()) != EXPECTED_MUTATIONS:
        print(f"FAIL     expected {EXPECTED_MUTATIONS} mutations, "
              f"found {len(mutations())}")
        failures += 1

    for name, inst in (("container", "container.xml"), ("metadata", "metadata.xml"),
                       ("manifest", "manifest.xml"), ("navigation", "nav.xml")):
        doc = etree.parse(os.path.join(EXAMPLES, inst))
        if rng[name].validate(doc):
            print(f"ok       {inst} validates")
        else:
            failures += 1
            print(f"FAIL     {inst} should validate")
            for e in rng[name].error_log:
                print("        ", e.message)

    for label, schema, inst, fn in mutations():
        doc = etree.parse(os.path.join(EXAMPLES, inst))
        fn(doc.getroot())
        if rng[schema].validate(doc):
            failures += 1
            print(f"FAIL     not rejected: {label}")
        else:
            print(f"ok       rejected: {label}")

    print(f"\n{'FAILED' if failures else 'PASSED'}: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
