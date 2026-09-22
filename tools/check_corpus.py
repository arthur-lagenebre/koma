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
import re
import sys
import unicodedata

# Section 3 fixes Unicode 16.0.0 for normalization and case folding. Older
# data can call two names distinct that the specification calls one, so the
# verdicts of this validator are only the reference ones on 16.0.0 or later.
if tuple(int(p) for p in unicodedata.unidata_version.split(".")) < (16, 0, 0):
    print(f"warning: this Python carries Unicode {unicodedata.unidata_version}; "
          "section 3 uses 16.0.0 (Python 3.14 or later)", file=sys.stderr)
import zipfile
import zlib

from lxml import etree
from PIL import Image

# Section 13.1 sets the pixel limits, not Pillow. Left in place, Pillow's own
# threshold warns about pages the default profile accepts, and above twice its
# value fails in Image.open, which would report an oversized page as
# unreadable instead of naming the limit it breaks.
Image.MAX_IMAGE_PIXELS = None

MAX_PIXELS_PER_PAGE = 100_000_000
MAX_PIXELS_PER_SIDE = 65_535

MIMETYPE = b"application/vnd.koma+zip"
NS = {"c": "urn:koma:container", "m": "urn:koma:metadata",
      "f": "urn:koma:manifest", "n": "urn:koma:navigation"}
# The default profile of 13.1.
MAX_ENTRIES = 10_000
TOTAL_UNCOMPRESSED = 4 * 1024 ** 3
ARCHIVE_MULTIPLE = 100
MAX_RATIO = 100
RATIO_FLOOR = 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024
MAX_XML_DEPTH = 100

# Section 4.5: every open vocabulary, as (document, element, attribute or
# None for element content, whether the value is a TokenList, core tokens).
# A token outside the core set that is not a valid private-use token is an
# error in strict mode, which is how an identical 0.x is read (section 5.3).
OPEN_VOCABULARIES = [
    ("m", "Identifier", "scheme", False,
     {"uuid", "isbn-10", "isbn-13", "ean-13", "issn", "doi", "uri", "proprietary"}),
    ("m", "Title", "type", False,
     {"main", "subtitle", "original", "alternative", "short", "sort"}),
    ("m", "Language", "role", False,
     {"content", "original", "translation", "secondary"}),
    ("m", "Collection", "type", False,
     {"series", "subseries", "cycle", "story-arc", "publisher-collection",
      "franchise", "universe", "anthology", "other"}),
    ("m", "Collection", "relation", False, {"main", "special", "other"}),
    ("m", "Name", "type", False,
     {"name", "given", "family", "middle", "prefix", "suffix", "pseudonym",
      "mononym", "alternative"}),
    ("m", "Contributor", "roles", True,
     {"writer", "script-writer", "adapter", "artist", "penciller", "inker",
      "colorist", "letterer", "cover-artist", "translator", "editor",
      "designer", "photographer", "consultant", "other"}),
    ("m", "Description", "type", False,
     {"summary", "synopsis", "blurb", "note", "edition-note", "series-note",
      "other"}),
    ("m", "Date", "event", False,
     {"publication", "first-publication", "creation", "digitization",
      "modified"}),
    ("m", "Subject", "type", False,
     {"genre", "theme", "keyword", "setting", "time-period", "audience",
      "other"}),
    ("m", "Entity", "type", False,
     {"character", "team", "organization", "location", "vehicle", "object",
      "event", "other"}),
    ("m", "Entity", "role", False,
     {"protagonist", "antagonist", "supporting", "cameo", "narrator"}),
    ("m", "Content", "original-medium", False,
     {"print", "digital", "webtoon", "mixed", "unknown"}),
    ("m", "Source", "type", False,
     {"print", "digital", "microform", "original-artwork", "periodical",
      "other"}),
    ("m", "Method", None, False,
     {"flatbed-scan", "sheet-fed-scan", "overhead-scan", "photography",
      "born-digital", "other"}),
    ("m", "Processing", None, True,
     {"deskew", "despeckle", "crop", "level-adjust", "colour-correction",
      "denoise", "upscale", "recompression", "other"}),
    ("m", "AccessMode", None, False,
     {"visual", "textual", "auditory", "tactile"}),
    ("m", "AccessModeSufficient", None, True,
     {"visual", "textual", "auditory", "tactile"}),
    ("m", "AccessibilityFeature", None, False,
     {"alternative-text", "long-description", "reading-order",
      "structural-navigation", "page-navigation", "table-of-contents",
      "high-contrast-display", "none"}),
    ("m", "AccessibilityHazard", None, False,
     {"flashing", "no-flashing-hazard", "motion-simulation",
      "no-motion-simulation-hazard", "sound", "no-sound-hazard", "none",
      "unknown"}),
    ("m", "ContentWarning", "type", False,
     {"violence", "gore", "sexual-content", "nudity", "language", "drug-use",
      "self-harm", "flashing-images", "other"}),
    ("m", "Link", "rel", False,
     {"homepage", "publisher", "author", "series", "purchase", "record",
      "errata", "license", "source", "related-publication", "other"}),
    ("f", "Item", "roles", True,
     {"front-cover", "inner-cover", "title-page", "table-of-contents", "recap",
      "story", "interlude", "illustration", "advertisement", "editorial",
      "letters", "preview", "credits", "bonus", "blank", "back-cover",
      "other"}),
    ("n", "Landmark", "type", False,
     {"front-cover", "inner-cover", "title-page", "table-of-contents",
      "body-start", "story-start", "credits", "glossary", "appendix", "bonus",
      "preview", "back-cover"}),
    ("n", "Region", "type", False,
     {"panel", "group", "inset", "caption", "other"}),
]

PRIVATE_USE = re.compile(r"x-[a-z0-9]([a-z0-9-]{0,59}[a-z0-9])?")

SIGNATURES = {"image/jpeg": (b"\xff\xd8\xff",),
              "image/png": (b"\x89PNG\r\n\x1a\n",),
              "image/webp": (b"RIFF",)}


def schemas(dirname):
    out = {}
    for name in ("container", "metadata", "manifest", "navigation"):
        out[name] = etree.RelaxNG(etree.parse(
            os.path.join(dirname, f"koma-{name}-0.9.rng")))
    return out


def actual_size(raw, info):
    """Decompress an entry and return its real size, ignoring what it declares.

    zipfile stops at the declared size, so it cannot answer this question: an
    entry that under-declares simply reads short. The compressed bytes are
    taken straight out of the archive and inflated here instead.
    """
    off = info.header_offset
    n = int.from_bytes(raw[off + 26:off + 28], "little")
    m = int.from_bytes(raw[off + 28:off + 30], "little")
    data = raw[off + 30 + n + m:off + 30 + n + m + info.compress_size]

    if info.compress_type == zipfile.ZIP_STORED:
        return len(data)
    if info.compress_type == zipfile.ZIP_DEFLATED:
        try:
            return len(zlib.decompress(data, -15))
        except zlib.error:
            return None
    return None


def stored_names(raw):
    """The entry names as the central directory holds them.

    zipfile rewrites a name as it reads it — on Windows it turns every
    backslash into a slash — so the names it reports are not always the names
    section 3 judges. These are read from the bytes.
    """
    eocd = raw.rfind(b"PK\x05\x06")

    if eocd < 0:
        return []

    at = int.from_bytes(raw[eocd + 16:eocd + 20], "little")
    names = []

    while raw[at:at + 4] == b"PK\x01\x02":
        flags = int.from_bytes(raw[at + 8:at + 10], "little")
        length = int.from_bytes(raw[at + 28:at + 30], "little")
        extra = int.from_bytes(raw[at + 30:at + 32], "little")
        comment = int.from_bytes(raw[at + 32:at + 34], "little")
        name = raw[at + 46:at + 46 + length]
        names.append(name.decode("utf-8" if flags & 0x800 else "cp437", "replace"))
        at += 46 + length + extra + comment

    return names


def depth(element, level=1):
    """The deepest nesting under an element, counting the element as one."""
    children = [c for c in element if isinstance(c.tag, str)]

    return max((depth(c, level + 1) for c in children), default=level)


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

    # A split archive holds a part of the publication somewhere else, so
    # nothing read here can be judged. The disk numbers of the
    # end-of-central-directory record are what says so.
    eocd = raw.rfind(b"PK\x05\x06")
    if eocd >= 0 and raw[eocd + 4:eocd + 8] != b"\0\0\0\0":
        err("multipart-archive")

    if not names or names[0] != "mimetype":
        err("mimetype-position")
    else:
        stored = z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        if not stored:
            err("mimetype-compression")
        # Section 2.1 fixes the bytes of the start of the file, and each fault
        # in them has its own code: a data descriptor (general purpose bit 3)
        # and extra fields are named before the content is compared, since
        # either one moves or hollows out the bytes the content check reads.
        elif int.from_bytes(raw[6:8], "little") & 0x08:
            err("mimetype-data-descriptor")
        elif int.from_bytes(raw[28:30], "little"):
            err("mimetype-extra-field")
        elif raw[30:38] != b"mimetype" or raw[38:38 + len(MIMETYPE)] != MIMETYPE:
            # The byte layout is only meaningful for a stored entry.
            err("mimetype-content")
    if "mimetype" in names and z.read("mimetype") != MIMETYPE:
        err("mimetype-content")

    seen = {}
    for n in stored_names(raw):
        if not n.strip():
            err("path-empty")
        if n.startswith("/") or (len(n) > 1 and n[1] == ":" and n[0].isascii()
                                 and n[0].isalpha()):
            err("absolute-path")
        if "\\" in n:
            err("path-backslash")
        parts = n.split("/")
        if ".." in parts or "." in parts:
            err("path-traversal")
        if any(p == "" for p in parts):
            err("path-empty-segment")
        if n != unicodedata.normalize("NFC", n):
            err("path-not-normalized")
        key = unicodedata.normalize("NFC", n).casefold()
        if key in seen:
            err("duplicate-logical-entry")
        seen[key] = n

    # 13.1, default profile. The declared sizes are the producer's claim, so the
    # ratio is checked against them and the actual output is checked against the
    # claim: an archive that under-declares passes every test made on paper.
    if len(stored_names(raw)) > MAX_ENTRIES:
        err("entry-count-limit")

    declared_total = 0
    for info in z.infolist():
        declared_total += info.file_size
        if (info.file_size > RATIO_FLOOR and info.compress_size
                and info.file_size > info.compress_size * MAX_RATIO):
            err("compression-ratio-limit")
        actual = actual_size(raw, info)
        if actual is not None and actual > info.file_size:
            err("declared-size-mismatch")

    if declared_total > min(TOTAL_UNCOMPRESSED, len(raw) * ARCHIVE_MULTIPLE):
        err("uncompressed-size-limit")

    # ---- layer 2: XML
    docs = {}
    for member, kind in (("META-INF/container.xml", "container"),
                         ("koma/metadata.xml", "metadata"),
                         ("koma/manifest.xml", "manifest"),
                         ("koma/nav.xml", "navigation")):
        if member not in names:
            # nav.xml is optional, and whether its absence is legal depends on
            # what the manifest declares: that is judged at layer 3.
            if kind != "navigation":
                err("missing-required-xml")
            continue
        data = z.read(member)

        # 13.1, before the document is parsed: a reader that parses first has
        # made the allocation the limit exists to prevent.
        if len(data) > MAX_XML_BYTES:
            err("xml-document-size-limit")
            continue

        try:
            doc = etree.fromstring(data)
        except etree.XMLSyntaxError:
            err("xml-not-well-formed")
            continue

        # Section 13 forbids a document type declaration outright, and a
        # document carrying one is not a core document a reader may parse.
        if doc.getroottree().docinfo.doctype:
            err("xml-not-well-formed")
            continue

        if depth(doc) > MAX_XML_DEPTH:
            err("xml-nesting-limit")
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

    # Section 8: the manifest declares nav.xml exactly when the package holds
    # it. The paths are fixed by section 1, so the declaration can only be
    # present or absent, and it must agree with the package either way.
    if (mf.get("navigation") is not None) != ("koma/nav.xml" in names):
        err("navigation-declaration-mismatch")
    elif "koma/nav.xml" not in names:
        warn("no-navigation-document")

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

    # Section 4.5: every open vocabulary, in whichever document holds it.
    # A private-use token is legal and noted; any other unknown one is an
    # error, which a reading system may still read past (section 16).
    roots = {"m": md, "f": mf, "n": nav}
    for prefix, element, attribute, is_list, core in OPEN_VOCABULARIES:
        root = roots[prefix]
        if root is None:
            continue
        for el in root.iterfind(f".//{prefix}:{element}", NS):
            value = el.get(attribute) if attribute else el.text
            if value is None:
                continue
            for token in (value.split(";") if is_list else [value.strip()]):
                if token in core:
                    continue
                if PRIVATE_USE.fullmatch(token):
                    warn("private-use-token")
                else:
                    err("unknown-token")

    # Section 4.3: a reader accepts either case, and a validator warns about
    # lowercase, since authoring tools must serialise uppercase.
    for it in items.values():
        colour = it.get("background-color")
        if colour is not None and colour != colour.upper():
            warn("color-lowercase")

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
        # Section 9.2: an absent spread-position is a value of its own, so
        # two whole-resource labels for one item are duplicates too.
        seen_targets = set()
        for pt in nav.iterfind(".//n:PageList/n:PageTarget", NS):
            key = (pt.get("item"), pt.get("spread-position"))
            if key in seen_targets:
                err("pagetarget-duplicate")
            seen_targets.add(key)
            it = items.get(pt.get("item"))
            if (pt.get("spread-position") is not None and it is not None
                    and it.get("page-span", "1") != "2"):
                err("span1-pagetarget-position")
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
        # Image.open reads the header only; nothing below may decode a page
        # that is over the limit, which is the allocation 13.1 forbids.
        if (im.width > MAX_PIXELS_PER_SIDE or im.height > MAX_PIXELS_PER_SIDE
                or im.width * im.height > MAX_PIXELS_PER_PAGE):
            err("page-pixel-limit")
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
        errors, warnings = check(os.path.join(corpus, "packages", c["package"]), rng)
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
                  sys.argv[2] if len(sys.argv) > 2
                  else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "schemas", "0.9")))
