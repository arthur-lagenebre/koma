"""Reference implementation of the KOMA 0.9 rendering model (spec section 10).

This is normative-by-example: a conforming reading system must produce the same
sequence of spreads for the same input. It implements section 10.3 (effective
spread position) and section 10.4 (pairing algorithm) and nothing else.

A spine entry is a dict:
    {"item": str, "page_span": 1|2, "spread_position": "auto"|"left"|"right"|"center",
     "roles": [str, ...]}

Output is a list of spreads. A spread is one of:
    {"center": item}                  a full-width spread (10.3 rules 1, 2, 4)
    {"left": item|None, "right": item|None}   a two-half spread
"""

# The normative pseudocode of section 10.4, transcribed verbatim.
# tests/test_spread.py compares this string with the specification, so the
# prose and this file cannot drift apart the way they did once: the fourth
# draft changed paginate() and the surrounding paragraph but left the
# pseudocode back-filling, and nothing noticed.
PSEUDOCODE = """\
buffer := empty
for each entry E in spine order:
    p := effective position of E (§10.3)
    if p is full:
        if buffer is not empty: emit(buffer); buffer := empty
        emit(spread containing only E, centered)
    else if p is fixed:
        if the requested side is occupied in buffer:
            emit(buffer); buffer := empty
        place E on the requested side of buffer
        if buffer is full: emit(buffer); buffer := empty
    else:                                    # flow
        if buffer is not empty and the leading side is free:
            emit(buffer); buffer := empty    # spine-order invariant
        if the leading side of buffer is free:
            place E on the leading side
        else:
            place E on the trailing side
        if buffer is full: emit(buffer); buffer := empty
if buffer is not empty: emit(buffer)
"""

FULL = "full"
FIXED_LEFT = "fixed-left"
FIXED_RIGHT = "fixed-right"
FLOW = "flow"


def effective_position(entry):
    """Section 10.3. The order of the rules is normative."""
    if entry.get("page_span", 1) == 2:            # rule 1
        return FULL
    pos = entry.get("spread_position", "auto")
    if pos == "center":                            # rule 2
        return FULL
    if pos == "left":                              # rule 3
        return FIXED_LEFT
    if pos == "right":                             # rule 3
        return FIXED_RIGHT
    if "front-cover" in entry.get("roles", []):    # rule 4, auto only
        return FULL
    return FLOW                                    # rule 5


def paginate(spine, direction, spread_mode, viewport_allows_two_up=True):
    """Section 10.1 and 10.4.

    `spread_mode` is the value of Reading/@spread: none | auto | force.
    `viewport_allows_two_up` models the display surface, not the publication.
    """
    if not two_up(spread_mode, viewport_allows_two_up):
        # Section 10.1: single mode. spread_position has no effect.
        return [{"single": e["item"]} for e in spine]

    leading = "left" if direction == "ltr" else "right"
    trailing = "right" if leading == "left" else "left"

    spreads = []
    buf = {"left": None, "right": None}

    def empty():
        return buf["left"] is None and buf["right"] is None

    def full():
        return buf["left"] is not None and buf["right"] is not None

    def flush():
        if not empty():
            spreads.append({"left": buf["left"], "right": buf["right"]})
            buf["left"] = buf["right"] = None

    for entry in spine:
        p = effective_position(entry)
        if p == FULL:
            flush()
            spreads.append({"center": entry["item"]})
        elif p in (FIXED_LEFT, FIXED_RIGHT):
            side = "left" if p == FIXED_LEFT else "right"
            if buf[side] is not None:
                flush()
            buf[side] = entry["item"]
            if full():
                flush()
        else:
            # A flowing item never back-fills the leading half of a spread
            # whose trailing half is already taken: doing so would place a
            # later spine entry on the side read first, contradicting section
            # 8.8. The half-spread is emitted instead.
            if not empty() and buf[leading] is None:
                flush()
            if buf[leading] is None:
                buf[leading] = entry["item"]
            else:
                buf[trailing] = entry["item"]
            if full():
                flush()
    flush()
    return spreads


def two_up(spread_mode, viewport_allows_two_up):
    """Section 10.1."""
    if spread_mode == "none":
        return False
    if spread_mode == "force":
        return viewport_allows_two_up
    return viewport_allows_two_up  # "auto": the reading system decides
