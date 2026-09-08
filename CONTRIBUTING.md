# Contributing to KOMA

## The rule that matters

**Normative text and executable artifacts travel together.** A commit that changes a MUST, a SHOULD, a vocabulary or a data type also updates the schemas, the corpus or the fixtures in the same commit. A commit that changes an artifact without changing the specification is either a bug fix in the artifact, and says so, or it is silently redefining the format.

CI enforces the half it can see: schemas, pairing cases and corpus must agree with each other. It cannot tell whether they agree with the prose. That part is on review.

## Never regenerate expectations from implementations

`tools/spread_cases.py` holds the expected pagination for §10, and every entry is written by reading the specification. If a case fails, the answer is one of:

- the implementation is wrong, so fix `tools/koma_spread.py`;
- the expectation is wrong, so fix the case **and say which sentence of §10 you read to get the new value**;
- the specification is ambiguous, so fix §10 first.

The one thing you must not do is paste the implementation's output into the expectations. The same applies to `corpus/expected.json`.

## Versioning discipline

The serialized version is `0.9`, a development version under §5.0.

While the major version is 0, incompatible changes are allowed and the number does not have to move — as long as no `0.9` file exists outside this repository. **Once a `0.9` file has been published anywhere**, any incompatible change needs a new number, because a reader supporting `0.9` must reject `0.10` and would otherwise be unable to tell the two apart. This rule is normative and lives in §5.0; what follows here is only how it plays out in practice.

The conformance corpus is excepted by §5.0: its packages are fixtures, regenerated whenever the format changes, so publishing the repository does not itself freeze the number.

Once the major version reaches 1, §5.2 applies: an addition in a minor version must be *safely ignorable*, meaning that discarding it leaves a publication that still renders correctly, only with less information. Anything else needs a major version. When in doubt, ask whether a reader that has never heard of your addition would produce a wrong result or merely a poorer one.

## Adding a corpus case

1. Add a `case(...)` entry in `tools/build_corpus.py` with the outcome, the error or warning code, and a note explaining what a reader gets wrong without the check.
2. Make it differ from `valid-minimal.koma` in exactly one respect. A package that trips three errors tests nothing precisely.
3. Regenerate with `python tools/build_corpus.py`. It writes to the repository corpus whatever the working directory, and `--out` sends it elsewhere.
4. Run `python tests/test_corpus.py`. Both the committed and rebuilt packages must behave as declared.
5. Run `python tests/test_docs.py`. The package count is quoted in README.md and this is what keeps it true.

If the check does not exist yet in `tools/check_corpus.py`, add it there too, or the case will pass for the wrong reason.

## Counters live in one place

README.md quotes how many mutations, pairing cases, corpus packages and CBZ fixtures the suites carry, and `tests/test_docs.py` recomputes all four and demands the exact sentence. Change a suite and that test fails until the prose follows.

Do not put a counter in CHANGELOG.md, unless it is inside double quotes: a quoted figure is a citation of past output and cannot go stale, so the test exempts it. An entry there is a historical record, and no test that only knows the present can keep it true; three of them drifted before this rule existed. The same test rejects a live counter reappearing in that file.

## What the tests are for

Five suites, all of which CI runs: `test_schemas` for layer 2, `test_spread` for §10, `test_corpus` for §15.1, `test_converter` for the CBZ path, `test_docs` for the counters above.

Normative prose that no test reads is worse still. §10.4 says its pseudocode is what a reading system MUST follow, so `tools/koma_spread.py` carries that pseudocode verbatim in `PSEUDOCODE` and `tests/test_spread.py` compares the two. Edit the specification without touching the implementation and the suite goes red. This exists because it once went wrong: a draft added an invariant as a paragraph, changed the implementation to match, and left the pseudocode prescribing the opposite behaviour.

A test that cannot fail is worse than no test. When adding one, break the thing it watches and confirm it goes red before committing it. `test_converter` reads `/proc/self/fd` for exactly this reason: a leaked file handle is invisible on Linux and fatal on Windows, so without that check CI would have stayed green on a bug that made the suite unusable on half the platforms.

## Third-party material

Do not commit real comics, scans, page images or CBZ archives, in any directory, in any commit, even temporarily. Git keeps history. All test material is generated from flat colour fields by `tools/build_corpus.py` and the fixtures under `examples/`.

## Style

Specification text uses BCP 14 keywords in uppercase only; a lowercase "must" carries no weight and reads as an oversight. Core elements are PascalCase, attributes and tokens are lowercase or kebab-case. New tokens in an open vocabulary need a fallback entry in the table of §4.5.1, or they are unusable by older readers.

Python targets 3.10+ and the standard library plus `lxml`, `Pillow` and `rnc2rng`. Tools print their assumptions on stderr rather than guessing quietly.
