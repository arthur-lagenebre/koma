"""Run the four validation layers of KOMA 0.9 section 15 over the corpus.

This is not a complete validator. It implements the checks the corpus
exercises, and it exists to prove that each corpus package actually trips the
error it claims to trip. Anything it does not implement is reported as
uncovered rather than silently passing.
"""

import hashlib
import io
import json
import os
import sys
import unicodedata
import zipfile

from lxml import etree
from PIL import Image

MIMETYPE = b"application/vnd.koma+zip"
NS = {"c": "urn:koma:container", "m": "urn:koma:metadata",
      "f": "urn:koma:manifest", "n": "urn:koma:navigation"}
SIGNATURES = {"image/jpeg": (b"\xff\xd8\xff",),
              "image/png": (b"\x89PNG\r\n\x1a\n",),
              "image/webp": (b"RIFF",)}


def schemas(dirname):
    out = {}
    for name in ("container", "metadata", "manifest", "navigation"):
        out[name] = etree.RelaxNG(etree.parse(
            os.path.join(dirname, f"koma-{name}-0.9.rng")))
    return out


def check(path, rng):
    errors, warnings = [], []

    def err(code):
        if code not in errors:
            errors.append(code)

    def warn(code):
        if code not in warnings:
            warnings.append(code)

    raw = open(path, "rb").read()

    # ---- layer 1: container
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return ["not-a-zip"], []
    names = z.namelist()

    if not names or names[0] != "mimetype":
        err("mimetype-position")
    else:
        stored = z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        if not stored:
            err("mimetype-compression")
        elif raw[30:38] != b"mimetype" or raw[38:38 + len(MIMETYPE)] != MIMETYPE:
            # The byte layout is only meaningful for a stored entry.
            err("mimetype-content")
    if "mimetype" in names and z.read("mimetype") != MIMETYPE:
        err("mimetype-content")

    seen = {}
    for n in names:
        if n.startswith("/"):
            err("absolute-path")
        parts = n.split("/")
        if ".." in parts or "." in parts or "\\" in n:
            err("path-traversal")
        key = unicodedata.normalize("NFC", n).casefold()
        if key in seen:
            err("duplicate-logical-entry")
        seen[key] = n

    # ---- layer 2: XML
    docs = {}
    for member, kind in (("META-INF/container.xml", "container"),
                         ("koma/metadata.xml", "metadata"),
                         ("koma/manifest.xml", "manifest"),
                         ("koma/nav.xml", "navigation")):
        if member not in names:
            if kind != "navigation":
                err("missing-required-xml")
            else:
                warn("no-navigation-document")
            continue
        try:
            doc = etree.fromstring(z.read(member))
        except etree.XMLSyntaxError:
            err("xml-not-well-formed")
            continue
        if not rng[kind].validate(doc):
            err(f"schema-invalid:{kind}")
        docs[kind] = doc

    if "manifest" not in docs or "metadata" not in docs:
        return errors, warnings

    mf, md = docs["manifest"], docs["metadata"]
    nav = docs.get("navigation")

    # ---- layer 3: cross-document
    items = {}
    for it in mf.iterfind(".//f:Resources/f:Item", NS):
        items[it.get("id")] = it
    spine = [r.get("item") for r in mf.iterfind(".//f:Spine/f:ItemRef", NS)]

    for ref in spine:
        if ref not in items:
            err("spine-target-missing")
    if len(spine) != len(set(spine)):
        err("spine-duplicate-item")

    covers = [i for i, it in items.items()
              if "front-cover" in (it.get("roles") or "").split(";")]
    if len(covers) == 0:
        err("front-cover-missing")
    elif len(covers) > 1:
        err("front-cover-duplicate")
    else:
        if covers[0] not in spine:
            err("front-cover-not-in-spine")
        elif spine and spine[0] != covers[0]:
            warn("front-cover-not-first")

    for i in items:
        if i not in spine:
            warn("resource-outside-spine")

    for it in items.values():
        for token in (it.get("roles") or "").split(";"):
            if token.startswith("x-"):
                warn("private-use-token")

    declared = {it.get("href") for it in items.values()}
    for n in names:
        if n.startswith("pages/") and n not in declared:
            err("undeclared-page-resource")

    for ref in mf.iterfind(".//f:Spine/f:ItemRef", NS):
        pos = ref.get("spread-position")
        it = items.get(ref.get("item"))
        if it is not None and it.get("page-span") == "2" and pos in ("left", "right"):
            err("span2-spread-position")

    if nav is not None:
        for el in nav.iter():
            target = el.get("item")
            if target is not None and target not in spine:
                err("navigation-target-outside-spine")
        seen_types = set()
        for lm in nav.iterfind(".//n:Landmarks/n:Landmark", NS):
            if lm.get("type") in seen_types:
                err("landmark-duplicate-type")
            seen_types.add(lm.get("type"))

    # Section 4.6: foreign content must actually carry a foreign namespace,
    # which the schemas cannot express for the no-namespace case (section 17).
    # Section 4.3: a TokenList must not repeat a token.
    for doc in (md, mf) + ((nav,) if nav is not None else ()):
        for ext in doc.iter("{urn:koma:metadata}Extensions",
                            "{urn:koma:manifest}Extensions",
                            "{urn:koma:navigation}Extensions"):
            for el in ext.iter():
                if el is ext:
                    continue
                if not str(el.tag).startswith("{"):
                    err("unnamespaced-element-in-extensions")
        for el in doc.iter():
            for name in ("roles", "Processing"):
                value = el.get(name)
                if value and len(value.split(";")) != len(set(value.split(";"))):
                    err("tokenlist-duplicate")

    hazards = {e.text for e in md.iterfind(".//m:AccessibilityHazard", NS)}
    warns = {e.get("type") for e in md.iterfind(".//m:ContentWarning", NS)}
    if "no-flashing-hazard" in hazards and "flashing-images" in warns:
        err("accessibility-hazard-conflict")
    if md.find(".//m:Accessibility", NS) is None:
        warn("no-publication-accessibility")

    for it in items.values():
        acc = it.find("f:Accessibility", NS)
        if acc is not None and acc.get("decorative") == "true" \
                and acc.find("f:AlternativeText", NS) is not None:
            err("decorative-with-alternative-text")

    # ---- layer 4: resources
    for it in items.values():
        href = it.get("href")
        if href not in names:
            err("missing-page-resource")
            continue
        data = z.read(href)
        mt = it.get("media-type")
        if not any(data.startswith(s) for s in SIGNATURES.get(mt, ())):
            err("media-type-mismatch")
        try:
            im = Image.open(io.BytesIO(data))
        except Exception:
            err("unreadable-page-resource")
            continue
        if (str(im.width) != it.get("width")
                or str(im.height) != it.get("height")):
            err("dimensions-mismatch")
        if getattr(im, "is_animated", False):
            err("animated-page-resource")
        if im.getexif().get(274, 1) != 1:
            err("exif-orientation-residue")
        ck = it.find("f:Checksum", NS)
        if ck is not None and ck.text.strip() != hashlib.sha256(data).hexdigest():
            err("checksum-mismatch")

    return errors, warnings


def main(corpus, schema_dir):
    rng = schemas(schema_dir)
    expected = json.load(open(os.path.join(corpus, "expected.json")))["cases"]
    ok = miss = uncovered = 0
    for c in expected:
        errors, warnings = check(os.path.join(corpus, c["package"]), rng)
        want, code = c["outcome"], c["code"]
        if want == "valid":
            good = not errors
        elif want == "warning":
            good = not errors and code in warnings
        else:
            good = code in errors
        status = "ok  " if good else "MISS"
        if good:
            ok += 1
        else:
            miss += 1
        print(f"{status} {c['package']:42} "
              f"errors={errors or '-'} warnings={warnings or '-'}")
    print(f"\n{ok}/{ok + miss} corpus packages behave as declared")
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "corpus",
                  sys.argv[2] if len(sys.argv) > 2 else ".."))
