"""Pairing fixtures for KOMA 0.9 section 10.

Every expectation here is written by hand from the specification text, not
produced by the reference implementation. The implementation is then checked
against them, so that a bug in the implementation cannot silently redefine the
format. A third-party reading system must reproduce these exactly.

Shorthand for a spine entry: "id" | "id:span2" | "id@left" | "id@right"
| "id@center" | "id!cover" (roles contains front-cover).
"""


def entry(token):
    e = {"item": token, "page_span": 1, "spread_position": "auto", "roles": []}
    if ":span2" in token:
        e["item"] = token.split(":")[0]
        e["page_span"] = 2
    if "@" in e["item"]:
        e["item"], pos = e["item"].split("@")
        e["spread_position"] = pos
    if "!cover" in e["item"]:
        e["item"] = e["item"].replace("!cover", "")
        e["roles"] = ["front-cover"]
    return e


def spine(s):
    return [entry(t) for t in s.split()]


L, R, C = "left", "right", "center"


def pair(**kw):
    return {"left": kw.get(L), "right": kw.get(R)}


def centered(item):
    return {"center": item}


CASES = [
    dict(
        id="10.6-worked-example",
        note="The example printed in section 10.6. Cover alone by rule 4, "
             "then p1 leading (right, rtl), p2 trailing, the span-2 alone, "
             "and p3 left over on the leading side.",
        direction="rtl", spread="auto",
        spine="c!cover p1 p2 d:span2 p3",
        expected=[centered("c"), pair(right="p1", left="p2"),
                  centered("d"), pair(right="p3")],
    ),
    dict(
        id="same-spine-ltr",
        note="Identical spine read left to right. Only the physical sides "
             "change; the grouping is the same.",
        direction="ltr", spread="auto",
        spine="c!cover p1 p2 d:span2 p3",
        expected=[centered("c"), pair(left="p1", right="p2"),
                  centered("d"), pair(left="p3")],
    ),
    dict(
        id="cover-paired-explicitly",
        note="Rule 3 beats rule 4: an explicit side on the cover makes it "
             "pair with the next page instead of standing alone.",
        direction="rtl", spread="auto",
        spine="c@right!cover p1 p2",
        expected=[pair(right="c", left="p1"), pair(right="p2")],
    ),
    dict(
        id="no-cover-role",
        note="Without the front-cover role and without an explicit side, the "
             "first page simply flows. This is why rule 4 exists.",
        direction="ltr", spread="auto",
        spine="p1 p2 p3 p4",
        expected=[pair(left="p1", right="p2"), pair(left="p3", right="p4")],
    ),
    dict(
        id="span2-flushes-half-full-buffer",
        note="A span-2 item interrupts a pair in progress; the half-full "
             "spread is emitted before it.",
        direction="ltr", spread="auto",
        spine="p1 d:span2 p2 p3",
        expected=[pair(left="p1"), centered("d"),
                  pair(left="p2", right="p3")],
    ),
    dict(
        id="center-mid-sequence",
        note="spread_position=center behaves exactly like a span-2 item for "
             "pairing purposes.",
        direction="ltr", spread="auto",
        spine="p1 p2 x@center p3",
        expected=[pair(left="p1", right="p2"), centered("x"), pair(left="p3")],
    ),
    dict(
        id="fixed-side-already-occupied",
        note="A fixed page whose side is taken forces the current spread out "
             "and starts a new one, leaving a blank half.",
        direction="ltr", spread="auto",
        spine="p1 p2@left p3",
        expected=[pair(left="p1"), pair(left="p2", right="p3")],
    ),
    dict(
        id="fixed-trailing-then-flow",
        note="A page fixed to the trailing side leaves the leading half free, "
             "but a flowing page MUST NOT take it: p2 follows p1 in the spine "
             "and the leading side is read first, so filling it would invert "
             "the reading order (section 10.4, spine-order invariant). The "
             "half-spread is emitted and p2 opens the next one.",
        direction="ltr", spread="auto",
        spine="p1@right p2 p3",
        expected=[pair(right="p1"), pair(left="p2", right="p3")],
    ),
    dict(
        id="spine-order-invariant-rtl",
        note="Same situation mirrored. p1 is pinned to the left, which is the "
             "trailing side in rtl, so p2 cannot back-fill the right half.",
        direction="rtl", spread="auto",
        spine="p1@left p2 p3",
        expected=[pair(left="p1"), pair(right="p2", left="p3")],
    ),
    dict(
        id="alternating-fixed",
        note="Fully hand-positioned publication: every page states its side.",
        direction="rtl", spread="auto",
        spine="a@right b@left c@right d@left",
        expected=[pair(right="a", left="b"), pair(right="c", left="d")],
    ),
    dict(
        id="consecutive-span2",
        note="Two span-2 items in a row each get their own spread.",
        direction="rtl", spread="auto",
        spine="d1:span2 d2:span2",
        expected=[centered("d1"), centered("d2")],
    ),
    dict(
        id="single-mode-spread-none",
        note="Section 10.1: with spread=none the pairing algorithm is not "
             "run at all and spread_position is ignored.",
        direction="rtl", spread="none",
        spine="c!cover p1 p2@left d:span2",
        expected=[{"single": "c"}, {"single": "p1"},
                  {"single": "p2"}, {"single": "d"}],
    ),
    dict(
        id="single-mode-narrow-viewport",
        note="spread=force falls back to single mode when the viewport "
             "cannot show two items side by side.",
        direction="ltr", spread="force", viewport=False,
        spine="c!cover p1 p2",
        expected=[{"single": "c"}, {"single": "p1"}, {"single": "p2"}],
    ),
    dict(
        id="cover-not-first",
        note="Rule 4 keys on the role, not on the position in the spine. "
             "A misplaced cover still stands alone; layer 3 warns separately.",
        direction="ltr", spread="auto",
        spine="p1 c!cover p2",
        expected=[pair(left="p1"), centered("c"), pair(left="p2")],
    ),
    dict(
        id="odd-tail-leading-only",
        note="The final incomplete spread keeps the trailing half empty.",
        direction="rtl", spread="auto",
        spine="p1 p2 p3",
        expected=[pair(right="p1", left="p2"), pair(right="p3")],
    ),
]
