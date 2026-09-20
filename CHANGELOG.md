# Changelog

Specification changes are recorded in Annex B of `spec/koma-0.9.md`. This file
records repository-level changes.

**Numbers in this file are historical.** A count written here describes what a
past change delivered, and nothing can keep it true afterwards — three of them
had silently gone stale before `tests/test_docs.py` existed. Live counts belong
in README.md, where that test recomputes them. If an entry genuinely needs a
figure, put it in double quotes: the test reads quoting as the mark of a
citation and lets it through. It cannot tell tense from prose, so the quotes
are the convention that stands in for it.

## Unreleased

- §4.3, §4.5, §16: `unknown-token` for a token outside the core set of an open
  vocabulary that is not a valid private-use token, an error in strict mode,
  and `color-lowercase`, a warning. A reading system may present a publication
  with an unknown token after applying the fallbacks of §4.5.1, if it says so.
  `tools/check_corpus.py` checks all 25 open vocabularies, where it checked
  page roles only, and the corpus gains a case for each code.
- §9.2: the two page-list rules get codes, `pagetarget-duplicate` and
  `span1-pagetarget-position`, and `tools/check_corpus.py` checks them. Two
  targets both without `spread-position` count as duplicates. The corpus gains
  a case for each and `valid-page-list`, its first package with a page list.
  Its two-page spread was first labelled as if the publication read left to
  right; the right half, read first, now carries the earlier number.
- §13.1, §16: a reading system withholds a page resource it cannot show
  safely, may show one with any other layer-4 error if it says so, keeps a
  withheld page's place in the spine, and stops presenting the publication as
  complete. §13.1 says how a reader that checks pages lazily honours the
  rejection of a page beyond the pixel limits.
- §13.1, §15: the pixel limits of the default profile get a code,
  `page-pixel-limit`, are judged at layer 4 from the image header before any
  decoding, and have two corpus cases. `tools/check_corpus.py` no longer leaves
  them to Pillow's own, lower threshold. `unreadable-page-resource` points at
  §8.1 instead of §12.
- §1, §6, §8: the core documents have fixed paths. §1 named them while the
  attributes of §6 and §8 were typed `Path`, so `tools/check_corpus.py` read
  the names and koma-desktop followed the attributes; the two disagreed on a
  manifest declaring a `nav.xml` the package did not contain. The schemas now
  pin the three attributes, `navigation-declaration-mismatch` covers
  `@navigation` disagreeing with the package in either direction, and the
  validator judges that at layer 3 instead of warning at layer 2.
- `SHA256SUMS` had not been regenerated since the line-ending commit: most
  entries no longer matched and five tracked files were missing from it,
  unnoticed because nothing checked it. It is regenerated, and CI now fails
  when it disagrees with the tracked files in content or in coverage.
- Workflow actions moved off the Node 20 runtime: `checkout@v7`,
  `setup-python@v7`, `upload-artifact@v7`.

- §15.1 extended past the container layer. The section named only layer-1
  codes, while the reference validator already emitted twelve others that no
  corpus case exercises and no section defined, among them the whole
  `schema-invalid:` family and one warning. The table now covers every code the
  validator uses, with its layer and whether it is an error or a warning.

- §15.1 added: error codes. The corpus named errors and §15.1 required a
  validator to report a named error, but no section said those names were
  normative, nor what to call a defect the corpus does not exercise. Two
  conforming validators could produce incomparable output. The corpus
  vocabulary is declared normative and the container-layer gaps are filled;
  the conformance corpus moves to §15.2.
- Annex B: the two entries from the previous change were recorded under the
  second draft instead of the fifth, and are moved.

- §13.1 reworked after implementation review. The section made its limits
  RECOMMENDED and configurable while §15 counted them as container validation,
  so there was no threshold a validator could validate against. They become a
  normative default profile, raisable only by an explicit user action. The
  per-entry ratio clause excepted entries "within the absolute limits", which
  were the global totals, so no entry could ever trigger it; the exception is
  now a per-entry floor. Declared ZIP sizes are stated to be producer-chosen,
  with enforcement required during decompression as well.

- Third external review applied. The §10.4 pseudocode, which the section makes
  normative, still described the behaviour the previous draft had replaced;
  `tests/test_spread.py` now compares it byte for byte with the reference
  implementation. The `0.x` publication rule moved into §5.0, where the annex
  had been claiming it lived, with the conformance corpus excepted.
- `tests/test_spread.py` counts structural failures apart from case failures.
  A drifting pseudocode used to be reported as "14/15 pairing cases" while all
  fifteen cases passed, pointing the reader at a case that was fine.

- Second external review applied. `tests/test_converter.py` leaked three ZIP
  handles per run, which POSIX tolerates and Windows does not: the suite
  reported every assertion passing and then exited 1 during temporary
  directory cleanup. The handles are closed, and the test now reads
  /proc/self/fd so that Linux fails for the same reason Windows does.
- The three `LICENSE-*` files carry canonical text instead of pointing at
  URLs, restoring what deleting the host-provided `LICENSE` had removed.
- Counters moved out of this file and into README.md, where `tests/test_docs.py`
  now checks them against the artifacts. A changelog entry is a historical
  record and cannot be kept true by a test that only knows the present; three
  of them had silently gone stale.

- Repository laid out: specification, schemas, corpus, tools, tests, CI.
- Conformance corpus with `expected.json`.
- Hand-written pairing cases for section 10.
- CBZ to KOMA converter.

## 0.9

First numbered draft. Development version: see section 5.0 before producing
any file with it.
