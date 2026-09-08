#!/usr/bin/env python3
"""Convert a CBZ archive, with or without ComicInfo.xml, into a KOMA 0.9 package.

Usage:
    cbz_to_koma.py input.cbz output.koma [options]

Options:
    --direction ltr|rtl   Override the reading direction.
    --lang TAG            BCP 47 tag for the content language.
    --checksums           Emit a SHA-256 checksum for every page.
    --infer-spreads       Mark landscape pages as page-span="2".
    --no-comicinfo        Do not carry ComicInfo.xml into the package.
    --quiet               Report errors only.

The converter never invents information. Everything KOMA requires that
ComicInfo cannot supply is either derived from the file itself, taken from an
option, or reported as an assumption on stderr. Direction in particular is a
guess whenever ComicInfo does not say YesAndRightToLeft.
"""

import argparse
import datetime
import hashlib
import io
import os
import re
import sys
import unicodedata
import uuid
import zipfile
from xml.sax.saxutils import escape, quoteattr

from PIL import Image, ImageOps

MIMETYPE = "application/vnd.koma+zip"
KOMA_NS_UUID = uuid.uuid5(uuid.NAMESPACE_URL, "https://koma.invalid/ns/cbz")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

# Extensions worth opening. The media type is never taken from the name: it
# comes from the actual bytes in normalize_image, per section 8.1.
IMAGE_EXT = {".jpg", ".jpeg", ".jpe", ".png", ".webp",
             ".gif", ".bmp", ".tif", ".tiff"}

PAGE_TYPE_TO_ROLE = {
    "FrontCover": "front-cover", "InnerCover": "inner-cover",
    "Roundup": "recap", "Story": "story", "Advertisement": "advertisement",
    "Editorial": "editorial", "Letters": "letters", "Preview": "preview",
    "BackCover": "back-cover", "Other": "other", "Deleted": "other",
}

CREDIT_FIELDS = {
    "Writer": "writer", "Penciller": "penciller", "Inker": "inker",
    "Colorist": "colorist", "Letterer": "letterer",
    "CoverArtist": "cover-artist", "Editor": "editor",
    "Translator": "translator",
}


class Report:
    def __init__(self, quiet=False):
        self.notes, self.quiet = [], quiet

    def assume(self, msg):
        self.notes.append(("assumption", msg))

    def lossy(self, msg):
        self.notes.append(("dropped", msg))

    def dump(self):
        for kind, msg in self.notes:
            if self.quiet and kind != "error":
                continue
            print(f"  {kind}: {msg}", file=sys.stderr)


# ------------------------------------------------------------------ reading


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", name)]


def read_cbz(path):
    z = zipfile.ZipFile(path)  # closed by convert()
    images, comicinfo = [], None
    for info in z.infolist():
        if info.is_dir():
            continue
        base = os.path.basename(info.filename)
        if base.startswith(".") or "__MACOSX" in info.filename:
            continue
        if base.lower() == "comicinfo.xml":
            comicinfo = z.read(info.filename)
            continue
        if os.path.splitext(base)[1].lower() in IMAGE_EXT:
            images.append(info.filename)
    images.sort(key=natural_key)
    return z, images, comicinfo


def parse_comicinfo(blob, report):
    """Return a plain dict. Absent or unparsable ComicInfo yields {}."""
    if not blob:
        return {}
    from lxml import etree
    try:
        root = etree.fromstring(blob)
    except etree.XMLSyntaxError:
        report.lossy("ComicInfo.xml is not well-formed and was ignored")
        return {}
    ci = {}
    for child in root:
        tag = etree.QName(child).localname
        if tag == "Pages":
            ci["Pages"] = [dict(p.attrib) for p in child]
        elif child.text and child.text.strip():
            ci[tag] = child.text.strip()
    return ci


# ------------------------------------------------------------------ images


def normalize_image(data, name, report):
    """Return (bytes, media_type, width, height).

    Bytes are passed through untouched whenever the image is already a
    conforming KOMA page, so that JPEG data is never recompressed and ICC
    profiles survive.
    """
    im = Image.open(io.BytesIO(data))
    fmt = (im.format or "").upper()
    # Section 8.3 forbids removing an embedded ICC profile. Capture it before
    # any conversion, because im.convert() drops info keys.
    icc = im.info.get("icc_profile")
    animated = getattr(im, "is_animated", False)
    orientation = im.getexif().get(274, 1)
    cmyk = im.mode == "CMYK"

    conforming = fmt in ("JPEG", "PNG", "WEBP")
    if conforming and not animated and orientation == 1 and not cmyk:
        return data, {"JPEG": "image/jpeg", "PNG": "image/png",
                      "WEBP": "image/webp"}[fmt], im.width, im.height

    if animated:
        report.lossy(f"{name}: animated image, only the first frame is kept"
                     + (", and the page is re-encoded as PNG"
                        if fmt == "WEBP" else ""))
        im.seek(0)
    if orientation != 1:
        report.assume(f"{name}: EXIF orientation {orientation} applied to the pixels")
        im = ImageOps.exif_transpose(im)
    if cmyk:
        report.assume(f"{name}: CMYK converted to RGB, outside the base profile")
    if not conforming:
        report.assume(f"{name}: {fmt or 'unknown format'} re-encoded as PNG")

    im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    buf = io.BytesIO()
    if cmyk and icc:
        # The profile describes CMYK data that no longer exists after the
        # conversion to RGB; carrying it over would mislabel the pixels.
        report.lossy(f"{name}: ICC profile dropped, it describes the CMYK "
                     "source rather than the converted RGB page")
        icc = None
    if fmt == "JPEG":
        # Already lossy; re-encoding at high quality is cheaper in size than
        # promoting the page to PNG.
        im.convert("RGB").save(buf, "JPEG", quality=95, subsampling=0,
                               icc_profile=icc)
        return buf.getvalue(), "image/jpeg", im.width, im.height
    im.save(buf, "PNG", optimize=True, icc_profile=icc)
    return buf.getvalue(), "image/png", im.width, im.height


# ------------------------------------------------------------------ metadata


def el(tag, text=None, **attrs):
    a = "".join(f" {k.replace('_', '-')}={quoteattr(str(v))}"
                for k, v in attrs.items() if v is not None)
    if text is None:
        return f"<{tag}{a}/>"
    return f"<{tag}{a}>{escape(str(text))}</{tag}>"


def split_credits(value):
    return [p.strip() for p in re.split(r"[,;]", value) if p.strip()]


MAPPED_FIELDS = {
    "Title", "Series", "Number", "Count", "Summary", "Notes", "Year", "Month",
    "Day", "Publisher", "Imprint", "Genre", "LanguageISO", "Manga",
    "BlackAndWhite", "AgeRating", "Web", "Pages",
} | set(CREDIT_FIELDS)

# Fields KOMA derives from the package itself, so carrying them would create a
# second source of truth rather than add information.
REDUNDANT_FIELDS = {"PageCount"}


def report_unmapped(ci, report):
    unmapped = sorted(set(ci) - MAPPED_FIELDS - REDUNDANT_FIELDS)
    if unmapped:
        report.lossy("ComicInfo fields with no KOMA equivalent, kept only in "
                     "the ComicInfo passthrough: " + ", ".join(unmapped))
    redundant = sorted(set(ci) & REDUNDANT_FIELDS)
    if redundant:
        report.lossy("ComicInfo fields recomputed from the package rather "
                     "than trusted: " + ", ".join(redundant) + ". The "
                     "passthrough copy still carries the original values, "
                     "which is the section 15 warning "
                     "'ComicInfo projection inconsistent with KOMA'")


def build_metadata(ci, args, page_digests, report):
    report_unmapped(ci, report)
    ident = uuid.uuid5(KOMA_NS_UUID,
                       hashlib.sha256("".join(page_digests).encode()).hexdigest())

    title = ci.get("Title")
    series = ci.get("Series")
    if not title:
        if series and ci.get("Number"):
            title = f"{series} {ci['Number']}"
            report.assume(f"no Title in ComicInfo; built {title!r} from Series "
                          "and Number")
        elif series:
            title = series
            report.assume(f"no Title in ComicInfo; using the series name {title!r}")
        else:
            title = args.fallback_title
            report.assume(f"no title in ComicInfo, using {title!r}")

    lang = args.lang or ci.get("LanguageISO")
    if not lang:
        lang = "und"
        report.assume("no language in ComicInfo, using the undetermined tag 'und'")

    manga = ci.get("Manga", "Unknown")
    if args.direction:
        direction = args.direction
    elif manga == "YesAndRightToLeft":
        direction = "rtl"
    else:
        direction = "ltr"
        report.assume(
            f"ComicInfo Manga={manga!r} does not state a reading direction; "
            "assuming ltr. Use --direction to set it.")

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<Metadata xmlns="urn:koma:metadata" version="0.9" xml:lang={quoteattr(lang)}>',
           "  <Identifiers>",
           f'    {el("Identifier", f"urn:uuid:{ident}", scheme="uuid", primary="true")}',
           "  </Identifiers>",
           "  <Titles>",
           f'    {el("Title", title, type="main")}',
           "  </Titles>",
           "  <Languages>",
           f'    {el("Language", lang, role="content")}',
           "  </Languages>"]

    if series:
        position = f" position={quoteattr(ci['Number'])}" if ci.get("Number") else ""
        total = f" total={quoteattr(ci['Count'])}" if ci.get("Count") else ""
        out += ["  <Collections>",
                f'    <Collection type="series"{position}{total}>',
                f'      {el("Name", series)}',
                "    </Collection>",
                "  </Collections>"]

    contributors = []
    for field, role in CREDIT_FIELDS.items():
        for person in split_credits(ci.get(field, "")):
            contributors.append((person, role))
    if contributors:
        merged = {}
        for person, role in contributors:
            merged.setdefault(person, []).append(role)
        report.assume("ComicInfo does not distinguish people from "
                      "organizations; every credit is written as "
                      'type="person": ' + ", ".join(merged))
        out.append("  <Contributors>")
        for person, roles in merged.items():
            out += [f'    <Contributor type="person" roles={quoteattr(";".join(dict.fromkeys(roles)))}>',
                    f'      {el("Name", person)}',
                    "    </Contributor>"]
        out.append("  </Contributors>")

    descriptions = []
    if ci.get("Summary"):
        descriptions.append(el("Description", ci["Summary"], type="summary"))
    if ci.get("Notes"):
        descriptions.append(el("Description", ci["Notes"], type="note"))
    if descriptions:
        out += ["  <Descriptions>"] + [f"    {d}" for d in descriptions] + ["  </Descriptions>"]

    pub = []
    if ci.get("Publisher"):
        pub.append(el("Publisher", ci["Publisher"]))
    if ci.get("Imprint"):
        pub.append(el("Imprint", ci["Imprint"]))
    date = comicinfo_date(ci)
    if date:
        pub.append(el("Date", date, event="publication"))
    # Taken from the source archive, not from the clock, so that converting
    # the same CBZ twice yields the same release identity (section 7.2.1).
    if args.modified:
        pub.append(el("Date", args.modified, event="modified"))
    if pub:
        out += ["  <Publication>"] + [f"    {p}" for p in pub] + ["  </Publication>"]

    genres = split_credits(ci.get("Genre", ""))
    if genres:
        out += ["  <Subjects>"] + \
               [f'    {el("Subject", g, type="genre")}' for g in genres] + \
               ["  </Subjects>"]

    out.append(f'  {el("Reading", direction=direction, spread="auto")}')

    bw = ci.get("BlackAndWhite")
    if bw == "Yes":
        out.append(f'  {el("Content", color_mode="monochrome")}')
    elif bw == "No":
        report.assume("ComicInfo BlackAndWhite=No rules out monochrome but "
                      "does not distinguish color from mixed; writing "
                      'color-mode="color"')
        out.append(f'  {el("Content", color_mode="color")}')

    if ci.get("AgeRating") and ci["AgeRating"] != "Unknown":
        out += ["  <Ratings>",
                f'    {el("Rating", scheme="comicinfo-agerating", value=ci["AgeRating"])}',
                "  </Ratings>"]

    links = []
    if ci.get("Web"):
        for url in ci["Web"].split():
            links.append(el("Link", rel="other", href=url))
    if links:
        out += ["  <Links>"] + [f"    {l}" for l in links] + ["  </Links>"]

    # Provenance records only what the conversion actually knows. The
    # digitization method is deliberately absent: a CBZ may hold a scan or a
    # born-digital export and nothing in the archive says which.
    out += ["  <Provenance>",
            f'    {el("Note", "Converted from a CBZ archive.")}',
            "  </Provenance>",
            "</Metadata>", ""]
    return "\n".join(out), direction


def comicinfo_date(ci):
    y, m, d = ci.get("Year"), ci.get("Month"), ci.get("Day")
    if not y:
        return None
    if m and d:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    if m:
        return f"{int(y):04d}-{int(m):02d}"
    return f"{int(y):04d}"


# ------------------------------------------------------------------ manifest


def build_manifest(pages, checksums, has_nav):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<Manifest xmlns="urn:koma:manifest" version="0.9"',
             '          metadata="koma/metadata.xml"' +
             ('' if not has_nav else '\n          navigation="koma/nav.xml"') + '>',
             "  <Resources>"]
    for p in pages:
        attrs = dict(id=p["id"], href=p["href"], media_type=p["media_type"],
                     width=p["width"], height=p["height"], roles=p["roles"])
        if p["span"] == 2:
            attrs["page_span"] = "2"
        if checksums:
            attr_text = "".join(
                f" {k.replace('_', '-')}={quoteattr(str(v))}"
                for k, v in attrs.items() if v is not None)
            lines.append(f"    <Item{attr_text}>")
            lines.append(f'      <Checksum algorithm="sha-256">{p["sha256"]}</Checksum>')
            lines.append("    </Item>")
        else:
            lines.append("    " + el("Item", **attrs))
    lines.append("  </Resources>")
    lines.append("  <Spine>")
    for p in pages:
        lines.append(f'    {el("ItemRef", item=p["id"])}')
    lines += ["  </Spine>", "</Manifest>", ""]
    return "\n".join(lines)


LANDMARK_FROM_ROLE = {"front-cover": "front-cover", "inner-cover": "inner-cover",
                      "title-page": "title-page", "back-cover": "back-cover"}


def build_nav(pages, page_list, report):
    """PageList is opt-in on purpose.

    Section 9.2 says a page label is the logical or printed page number. A CBZ
    only knows the scan order, and in a real book the two differ: the cover and
    the inner cover carry no printed number, so labelling the third image "3"
    states something false. Numbering from the scan order is offered under
    --page-list for collections that want positional labels, and is off by
    default.
    """
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<Navigation xmlns="urn:koma:navigation" version="0.9">']

    if page_list:
        report.assume("--page-list: labels number the scan order, which is not "
                      "the printed pagination")
        lines.append("  <PageList>")
        logical = 0
        for p in pages:
            if p["span"] == 2:
                lines.append(f'    {el("PageTarget", item=p["id"], label=str(logical + 1), spread_position="left")}')
                lines.append(f'    {el("PageTarget", item=p["id"], label=str(logical + 2), spread_position="right")}')
                logical += 2
            else:
                logical += 1
                lines.append(f'    {el("PageTarget", item=p["id"], label=str(logical))}')
        lines.append("  </PageList>")

    seen, marks = set(), []
    for p in pages:
        lm = LANDMARK_FROM_ROLE.get(p["roles"])
        if lm and lm not in seen:
            seen.add(lm)
            marks.append(f'    {el("Landmark", type=lm, item=p["id"])}')
    for p in pages:
        if p["roles"] == "story":
            marks.append(f'    {el("Landmark", type="body-start", item=p["id"])}')
            break
    lines += ["  <Landmarks>"] + marks + ["  </Landmarks>", "</Navigation>", ""]
    return "\n".join(lines)


# ------------------------------------------------------------------ packaging


def write_koma(path, xml_files, pages_bytes, comicinfo):
    rest = {}
    for name, data in xml_files.items():
        rest[unicodedata.normalize("NFC", name)] = data.encode("utf-8")
    if comicinfo is not None:
        rest["ComicInfo.xml"] = comicinfo
    for name, data in pages_bytes.items():
        rest[unicodedata.normalize("NFC", name)] = data
    # Section 14.2: one ordering pass over every entry, byte-wise on the NFC
    # form, so that adding a directory cannot silently break the sort.
    entries = [("mimetype", MIMETYPE.encode(), True)]
    entries += [(n, rest[n], False) for n in sorted(rest, key=lambda x: x.encode())]
    with zipfile.ZipFile(path, "w") as z:
        for name, data, stored in entries:
            zi = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            zi.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)


CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<Container xmlns="urn:koma:container" version="0.9">
  <RootFiles>
    <RootFile full-path="koma/manifest.xml"
              media-type="application/vnd.koma.manifest+xml"/>
  </RootFiles>
</Container>
"""


# ------------------------------------------------------------------ driver


def newest_entry_date(z):
    """The most recent ZIP timestamp in the source archive, as an ISO date."""
    stamps = [i.date_time for i in z.infolist()]
    if not stamps:
        return None
    y, m, d = max(stamps)[:3]
    return f"{y:04d}-{m:02d}-{d:02d}"


def convert(args):
    report = Report(args.quiet)
    z, image_names, comicinfo_blob = read_cbz(args.input)
    if not args.modified:
        args.modified = newest_entry_date(z)
        if args.modified:
            report.assume(f"modified date taken from the archive timestamps "
                          f"({args.modified}); use --modified to set it")
    if not image_names:
        print("error: no image found in the archive", file=sys.stderr)
        return 1
    ci = parse_comicinfo(comicinfo_blob, report)

    ci_pages = {}
    for p in ci.get("Pages", []):
        try:
            ci_pages[int(p.get("Image", -1))] = p
        except ValueError:
            pass
    if ci.get("Pages") and len(ci["Pages"]) != len(image_names):
        report.lossy(f"ComicInfo declares {len(ci['Pages'])} pages but the "
                     f"archive holds {len(image_names)}; page metadata is "
                     "matched by index and may be off")

    # Width follows the page count, with a floor of three digits, so that a
    # 165-page album numbers 001..165 rather than 0001..0165.
    width = max(3, len(str(len(image_names))))

    pages, pages_bytes, digests = [], {}, []
    for index, name in enumerate(image_names):
        data, media_type, w, h = normalize_image(z.read(name), name, report)
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[media_type]
        href = f"pages/{index + 1:0{width}d}{ext}"
        meta = ci_pages.get(index, {})
        role = PAGE_TYPE_TO_ROLE.get(meta.get("Type", ""), None)
        span = 2 if meta.get("DoublePage", "").lower() == "true" else 1
        if span == 1 and args.infer_spreads and w > h * 1.2:
            span = 2
            report.assume(f"{name}: landscape page marked page-span=2")
        digest = hashlib.sha256(data).hexdigest()
        digests.append(digest)
        pages.append(dict(id=f"p{index + 1:0{width}d}", href=href, media_type=media_type,
                          width=w, height=h, roles=role, span=span, sha256=digest,
                          source=name))
        pages_bytes[href] = data

    covers = [p for p in pages if p["roles"] == "front-cover"]
    if not covers:
        pages[0]["roles"] = "front-cover"
        report.assume(f"no FrontCover in ComicInfo; {pages[0]['source']} taken as the cover")
    elif len(covers) > 1:
        for extra in covers[1:]:
            extra["roles"] = "inner-cover"
        report.assume(f"{len(covers)} pages marked FrontCover; kept the first, "
                      "demoted the others to inner-cover")
        for p in pages[1:]:
            if "cover" in os.path.basename(p["source"]).lower():
                report.assume(
                    f"{p['source']} looks like a cover but sorts after "
                    f"{pages[0]['source']}; the archive order was kept")
    elif covers[0] is not pages[0]:
        report.assume("the ComicInfo front cover is not the first page; "
                      "the spine keeps the archive order")
    untyped = [p for p in pages if p["roles"] is None]
    for p in untyped:
        p["roles"] = "story"
    if untyped:
        report.assume(f"{len(untyped)} of {len(pages)} pages carry no ComicInfo "
                      "type and default to 'story'")

    metadata, direction = build_metadata(ci, args, digests, report)
    nav = build_nav(pages, args.page_list, report) if not args.no_nav else None
    manifest = build_manifest(pages, args.checksums, nav is not None)

    xml_files = {"META-INF/container.xml": CONTAINER,
                 "koma/metadata.xml": metadata,
                 "koma/manifest.xml": manifest}
    if nav:
        xml_files["koma/nav.xml"] = nav

    report.assume(f"pages renumbered to pages/001..{len(pages):0{width}d} in "
                  "archive order; the source names are not preserved")
    keep_ci = comicinfo_blob if (comicinfo_blob and not args.no_comicinfo) else None
    if keep_ci and ci.get("Pages"):
        report.assume(
            "ComicInfo Page/@Image counts from 0 while page files count from 1: "
            f'Image="0" is pages/{1:0{width}d}, Image="N" is page N+1')
    write_koma(args.output, xml_files, pages_bytes, keep_ci)

    if not args.quiet:
        print(f"{args.input} -> {args.output}", file=sys.stderr)
        print(f"  {len(pages)} pages, direction={direction}, "
              f"{'with' if keep_ci else 'without'} ComicInfo passthrough",
              file=sys.stderr)
    z.close()
    report.dump()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert CBZ to KOMA 0.9")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--direction", choices=["ltr", "rtl"])
    ap.add_argument("--lang")
    ap.add_argument("--fallback-title", default="Untitled")
    ap.add_argument("--modified", help="ISO date for Publication/Date[@event=modified]")
    ap.add_argument("--checksums", action="store_true")
    ap.add_argument("--infer-spreads", action="store_true")
    ap.add_argument("--no-comicinfo", action="store_true")
    ap.add_argument("--no-nav", action="store_true")
    ap.add_argument("--page-list", action="store_true",
                    help="emit a PageList numbered from the scan order")
    ap.add_argument("--quiet", action="store_true")
    return convert(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
