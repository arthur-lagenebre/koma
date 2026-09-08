"""Build the KOMA 0.9 conformance corpus.

Produces one .koma package per case under corpus/, plus expected.json giving
the outcome a conforming validator must report for each. Cases are named after
the layer they exercise: L1 container, L2 XML, L3 cross-document, L4 resource.
"""

import hashlib
import io
import json
import os
import shutil
import zipfile

from PIL import Image

# The corpus lives at <repo>/corpus: expected.json beside a packages/
# directory. build() takes an explicit destination so that a rebuild for
# comparison cannot overwrite the committed corpus, and so that running this
# script from any working directory does the same thing.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, "corpus")
MIMETYPE = "application/vnd.koma+zip"

# ---------------------------------------------------------------- images


def img(w, h, fmt, colour=(220, 220, 220), **kw):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, fmt, **kw)
    return buf.getvalue()


def animated_webp(w, h):
    buf = io.BytesIO()
    frames = [Image.new("RGB", (w, h), c) for c in ((255, 0, 0), (0, 0, 255))]
    frames[0].save(buf, "WEBP", save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    return buf.getvalue()


def jpeg_with_orientation(w, h, orientation):
    im = Image.new("RGB", (w, h), (200, 200, 200))
    exif = im.getexif()
    exif[274] = orientation
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


PAGES = {
    "pages/001.jpg": img(800, 1200, "JPEG"),
    "pages/002.png": img(800, 1200, "PNG"),
    "pages/003.png": img(800, 1200, "PNG"),
    "pages/004.webp": img(1600, 1200, "WEBP"),
}

def sha256(b):
    return hashlib.sha256(b).hexdigest()

# ---------------------------------------------------------------- xml

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<Container xmlns="urn:koma:container" version="0.9">
  <RootFiles>
    <RootFile full-path="koma/manifest.xml"
              media-type="application/vnd.koma.manifest+xml"/>
  </RootFiles>
</Container>
"""

METADATA = """<?xml version="1.0" encoding="UTF-8"?>
<Metadata xmlns="urn:koma:metadata" version="0.9" xml:lang="fr">
  <Identifiers>
    <Identifier scheme="uuid" primary="true">urn:uuid:6f9619ff-8b86-d011-b42d-00c04fc964ff</Identifier>
  </Identifiers>
  <Titles>
    <Title type="main">Corpus de conformite</Title>
  </Titles>
  <Languages>
    <Language role="content">fr</Language>
  </Languages>
  <Reading direction="rtl" spread="auto"/>
  <Content color-mode="monochrome"/>
  <Accessibility>
    <AccessMode>visual</AccessMode>
    <AccessibilityHazard>no-flashing-hazard</AccessibilityHazard>
    <AccessibilitySummary xml:lang="fr">Pages decrites.</AccessibilitySummary>
  </Accessibility>
</Metadata>
"""

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<Manifest xmlns="urn:koma:manifest" version="0.9"
          metadata="koma/metadata.xml" navigation="koma/nav.xml">
  <Resources>
    <Item id="p001" href="pages/001.jpg" media-type="image/jpeg"
          width="800" height="1200" roles="front-cover">
      <Checksum algorithm="sha-256">{sum1}</Checksum>
      <Accessibility decorative="false">
        <AlternativeText xml:lang="fr">Couverture.</AlternativeText>
      </Accessibility>
    </Item>
    <Item id="p002" href="pages/002.png" media-type="image/png"
          width="800" height="1200" roles="story"/>
    <Item id="p003" href="pages/003.png" media-type="image/png"
          width="800" height="1200" roles="story"/>
    <Item id="p004" href="pages/004.webp" media-type="image/webp"
          width="1600" height="1200" roles="story" page-span="2"/>
  </Resources>
  <Spine>
    <ItemRef item="p001"/>
    <ItemRef item="p002"/>
    <ItemRef item="p003"/>
    <ItemRef item="p004"/>
  </Spine>
</Manifest>
"""

NAV = """<?xml version="1.0" encoding="UTF-8"?>
<Navigation xmlns="urn:koma:navigation" version="0.9" xml:lang="fr">
  <TableOfContents>
    <Entry item="p002"><Label xml:lang="fr">Chapitre 1</Label></Entry>
  </TableOfContents>
  <Landmarks>
    <Landmark type="front-cover" item="p001"/>
    <Landmark type="body-start" item="p002"/>
  </Landmarks>
</Navigation>
"""


def base_files():
    return {
        "koma/metadata.xml": METADATA,
        "koma/manifest.xml": MANIFEST.format(sum1=sha256(PAGES["pages/001.jpg"])),
        "koma/nav.xml": NAV,
        "META-INF/container.xml": CONTAINER,
    }

# ---------------------------------------------------------------- packaging


def write_package(path, xml_files, pages, mimetype=MIMETYPE,
                  mimetype_first=True, mimetype_stored=True, extra_entries=()):
    entries = []
    if mimetype_first:
        entries.append(("mimetype", mimetype.encode(), mimetype_stored))
    for name in sorted(xml_files):
        entries.append((name, xml_files[name].encode("utf-8"), False))
    for name in sorted(pages):
        entries.append((name, pages[name], False))
    for name, data in extra_entries:
        entries.append((name, data, False))
    if not mimetype_first:
        entries.append(("mimetype", mimetype.encode(), mimetype_stored))

    with zipfile.ZipFile(path, "w") as z:
        for name, data, stored in entries:
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = (zipfile.ZIP_STORED if stored
                                else zipfile.ZIP_DEFLATED)
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)


# ---------------------------------------------------------------- cases

CASES = []


def case(name, outcome, code, note, mutate=None, **pkg):
    CASES.append(dict(name=name, outcome=outcome, code=code, note=note,
                      mutate=mutate, pkg=pkg))


def sub(doc, old, new):
    """Return a mutator replacing `old` with `new` in `doc`."""
    def f(files, pages):
        assert old in files[doc], f"pattern not found in {doc}: {old!r}"
        files[doc] = files[doc].replace(old, new, 1)
    return f


def chain(*fns):
    def f(files, pages):
        for fn in fns:
            fn(files, pages)
    return f


M = "koma/manifest.xml"
D = "koma/metadata.xml"
N = "koma/nav.xml"

# --- valid -------------------------------------------------------------
case("valid-minimal", "valid", None,
     "Baseline package. Every other case is this one with one thing changed.")

case("valid-no-navigation", "warning", "no-navigation-document",
     "nav.xml absent. Legal, but a validator warns.",
     mutate=chain(
         lambda f, p: f.pop(N),
         sub(M, ' navigation="koma/nav.xml"', "")))

case("valid-private-use-tokens", "warning", "private-use-token",
     "x- tokens in an open vocabulary. Accepted, flagged.",
     mutate=sub(M, 'roles="story"', 'roles="story;x-splash"'))

# --- layer 1: container ------------------------------------------------
case("L1-mimetype-wrong-content", "error", "mimetype-content",
     "mimetype holds the old GRNO spelling.",
     mimetype="application/vnd.grno+zip")

case("L1-mimetype-not-first", "error", "mimetype-position",
     "mimetype present but not the first ZIP entry.",
     mimetype_first=False)

case("L1-mimetype-deflated", "error", "mimetype-compression",
     "mimetype stored with Deflate instead of Store.",
     mimetype_stored=False)

case("L1-path-traversal", "error", "path-traversal",
     "An entry escapes the package root.",
     extra_entries=[("../evil.txt", b"x")])

case("L1-absolute-path", "error", "absolute-path",
     "An entry name starts with a slash.",
     extra_entries=[("/etc/passwd", b"x")])

case("L1-case-fold-duplicate", "error", "duplicate-logical-entry",
     "Two entries differing only by case fold to the same logical name.",
     extra_entries=[("pages/001.JPG", PAGES["pages/001.jpg"])])

# --- layer 3: cross-document -------------------------------------------
case("L3-no-front-cover", "error", "front-cover-missing",
     "No item carries the front-cover role.",
     mutate=sub(M, ' roles="front-cover"', ' roles="inner-cover"'))

case("L3-two-front-covers", "error", "front-cover-duplicate",
     "Two items claim the front cover.",
     mutate=sub(M, 'href="pages/002.png" media-type="image/png"\n'
                   '          width="800" height="1200" roles="story"',
                'href="pages/002.png" media-type="image/png"\n'
                '          width="800" height="1200" roles="front-cover"'))

case("L3-private-token-as-cover", "error", "front-cover-missing",
     "A private-use token cannot satisfy the front-cover requirement.",
     mutate=sub(M, 'roles="front-cover"', 'roles="x-cover"'))

case("L3-cover-not-in-spine", "error", "front-cover-not-in-spine",
     "The cover exists but is not a reading resource.",
     mutate=sub(M, '<ItemRef item="p001"/>\n    ', ""))

case("L3-spine-target-missing", "error", "spine-target-missing",
     "An ItemRef points at an id that does not exist.",
     mutate=sub(M, '<ItemRef item="p003"/>', '<ItemRef item="p999"/>'))

case("L3-item-twice-in-spine", "error", "spine-duplicate-item",
     "The same item appears twice in the reading order.",
     mutate=sub(M, '<ItemRef item="p004"/>',
                '<ItemRef item="p002"/>\n    <ItemRef item="p004"/>'))

case("L3-nav-target-outside-spine", "error", "navigation-target-outside-spine",
     "A TOC entry targets an item that is not in the spine.",
     mutate=chain(sub(M, '<ItemRef item="p003"/>\n    ', ""),
                  sub(N, 'Entry item="p002"', 'Entry item="p003"')))

case("L3-span2-with-side", "error", "span2-spread-position",
     "A two-page image cannot be pinned to a physical side.",
     mutate=sub(M, '<ItemRef item="p004"/>',
                '<ItemRef item="p004" spread-position="left"/>'))

case("L3-hazard-contradiction", "error", "accessibility-hazard-conflict",
     "no-flashing-hazard declared alongside a flashing-images warning.",
     mutate=sub(D, "  </Accessibility>", """  </Accessibility>
  <Ratings>
    <ContentWarning type="flashing-images"/>
  </Ratings>"""))

case("L3-decorative-with-alt-text", "error", "decorative-with-alternative-text",
     "A page declared decorative also carries alternative text.",
     mutate=sub(M, 'decorative="false"', 'decorative="true"'))

case("L3-resource-not-in-spine", "warning", "resource-outside-spine",
     "A declared page is never read.",
     mutate=sub(M, '<ItemRef item="p003"/>\n    ', ""))

case("L3-cover-not-first", "warning", "front-cover-not-first",
     "The cover is in the spine but not at its head.",
     mutate=sub(M, '<ItemRef item="p001"/>\n    <ItemRef item="p002"/>',
                '<ItemRef item="p002"/>\n    <ItemRef item="p001"/>'))

case("L3-tokenlist-duplicate", "error", "tokenlist-duplicate",
     "A roles attribute repeats a token, which section 4.3 forbids.",
     mutate=sub(M, 'roles="story"', 'roles="story;story"'))

case("L3-unnamespaced-extension", "error", "unnamespaced-element-in-extensions",
     "An element in no namespace is neither core nor legal foreign content.",
     mutate=sub(D, "</Metadata>", """  <Extensions>
    <x xmlns=""/>
  </Extensions>
</Metadata>"""))

# --- layer 4: resources ------------------------------------------------
case("L4-media-type-mismatch", "error", "media-type-mismatch",
     "PNG bytes declared as JPEG.",
     mutate=sub(M, 'href="pages/002.png" media-type="image/png"',
                'href="pages/002.png" media-type="image/jpeg"'))

case("L4-wrong-dimensions", "error", "dimensions-mismatch",
     "Declared width does not match the raster.",
     mutate=sub(M, 'width="800" height="1200" roles="story"/>\n    <Item id="p003"',
                'width="801" height="1200" roles="story"/>\n    <Item id="p003"'))

case("L4-animated-page", "error", "animated-page-resource",
     "An animated WebP is used as a page.",
     pages_override={"pages/004.webp": animated_webp(1600, 1200)})

case("L4-failed-checksum", "error", "checksum-mismatch",
     "The declared digest does not match the stored bytes.",
     mutate=sub(M, sha256(PAGES["pages/001.jpg"]), "0" * 64))

case("L4-residual-exif-orientation", "error", "exif-orientation-residue",
     "The cover keeps an EXIF orientation of 6.",
     pages_override={"pages/001.jpg": jpeg_with_orientation(800, 1200, 6)})


# ---------------------------------------------------------------- main

def build(out=None):
    out = out or DEFAULT_OUT
    packages = os.path.join(out, "packages")
    if os.path.isdir(packages):
        shutil.rmtree(packages)
    os.makedirs(packages)
    expected = []
    for c in CASES:
        files = base_files()
        pages = dict(PAGES)
        pkg = dict(c["pkg"])
        for name, data in pkg.pop("pages_override", {}).items():
            pages[name] = data
        if c["mutate"]:
            c["mutate"](files, pages)
        # keep the cover checksum honest unless the case is about the checksum
        if c["name"] not in ("L4-failed-checksum",) and M in files:
            files[M] = files[M].replace(sha256(PAGES["pages/001.jpg"]),
                                        sha256(pages["pages/001.jpg"]))
        path = os.path.join(packages, c["name"] + ".koma")
        write_package(path, files, pages, **pkg)
        expected.append({"package": c["name"] + ".koma",
                         "outcome": c["outcome"],
                         "code": c["code"],
                         "note": c["note"]})
    with open(os.path.join(out, "expected.json"), "w") as f:
        json.dump({"specification": "KOMA 0.9", "cases": expected}, f,
                  indent=2, ensure_ascii=False)
    return expected


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Build the KOMA conformance corpus")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="destination directory (default: the repository corpus)")
    args = ap.parse_args()
    e = build(args.out)
    print(f"{len(e)} packages written to {os.path.join(args.out, 'packages')}/")
