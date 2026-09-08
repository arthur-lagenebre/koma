# KOMA

A fixed-page publication format for graphic novels, manga, bande dessinée, comics, manhwa and other sequential graphic works. It packages raster pages with structured metadata, an explicit reading spine, optional navigation, and optional ComicInfo interoperability metadata.

KOMA is a name, not an acronym. It comes from the Japanese コマ (*koma*), the panel — the smallest unit every one of those forms shares. It expands to nothing, and it deliberately does not name any single publishing category.

## Status: 0.9, pre-release

**Do not archive files produced with this version.** The serialized version is `0.9`, which is a development version under §5.0 of the specification: any `0.9` file may become unreadable when `1.0` lands, and a reader supporting one `0.x` must reject every other. The media type is not yet registered.

What is settled: the container profile, the four core documents and their schemas, the rendering model including the pairing algorithm, the versioning rules, the security requirements and the conformance corpus.

What raises the version to `1.0`, from §5.0.1:

1. two independent reading system implementations pass §16 — **open, and the only item that cannot be done alone**;
2. a validator implements the four layers of §15 — partly done, see `tools/check_corpus.py`;
3. the corpus covers every §15 error and every branch of §10.4 — done for §10.4; for §15, 6 errors are caught by the schemas, 2 more by `check_corpus.py`, and the majority are still uncovered;
4. the schemas are published and agree with the specification — done;
5. the media type is registered — not started.

## Layout

```text
spec/koma-0.9.md        the specification
schemas/0.9/            RELAX NG compact schemas and reference instances
corpus/                 conformance corpus and expected.json
tools/                  reference implementations and the CBZ converter
tests/                  what CI runs
examples/               synthetic CBZ fixtures
```

## Quickstart

```sh
pip install -r requirements.txt

python tests/test_schemas.py      # schemas accept the valid, reject 33 invalid
python tests/test_spread.py       # pairing against 15 hand-written cases
python tests/test_corpus.py       # committed and rebuilt corpus, 28 packages
python tests/test_converter.py    # 3 CBZ fixtures, conformance and determinism
python tests/test_docs.py         # the counters above, kept honest

python tools/cbz_to_koma.py in.cbz out.koma --direction rtl --checksums
```

The converter reports every assumption it makes on stderr. Read them: a CBZ rarely states its reading direction, and defaulting to `ltr` on a Japanese work would have every page read backwards.

## The corpus is normative by example

`corpus/expected.json` states, for each package, whether a conforming validator must report it valid, or carrying a named warning, or carrying a named error. Each package differs from `valid-minimal.koma` in exactly one respect. A validator that disagrees with `expected.json` does not conform; a disagreement the specification does not settle is a specification bug, not a corpus bug.

The pairing expectations in `tools/spread_cases.py` are written by hand from the prose of §10. They are never regenerated from `tools/koma_spread.py`, because an implementation that grades its own homework proves nothing.

## No third-party works here

Everything under `examples/` and `corpus/` is synthetic, generated from flat colour fields. Never commit a real comic, scan, or CBZ, however convenient it would be as a test file: it is redistribution. CI fails on any file over 2 MB, which catches the accident.

## Licences

| Part | Licence |
| --- | --- |
| `spec/` | CC BY 4.0 |
| `tools/`, `tests/` | Apache-2.0 |
| `corpus/`, `examples/` | CC0 1.0 |

The three `LICENSE-*` files carry the canonical text in full, taken from the SPDX license list. Apache-2.0 clause 4(a) requires that a copy travel with the work, so the file is not a link. If your host added a bare `LICENSE` file, delete it: it duplicates `LICENSE-CODE` and contradicts the table above.

## Contributing

See `CONTRIBUTING.md`. The short version: a change to normative text and a change to the corpus or the fixtures travel together in the same commit.
