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
