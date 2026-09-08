# KOMA 0.9 — Pre-release for KOMA 1.0

**Status:** Pre-release. The serialized version is `0.9`; the stable release will be `1.0`.  
**File extension:** `.koma`  
**Media type:** `application/vnd.koma+zip` (vendor tree; not yet IANA-registered)  
**Container:** ZIP only  
**Core XML encoding:** UTF-8

KOMA is a fixed-page publication format for graphic novels, manga, bande dessinée, comics, manhwa and other sequential graphic works. It packages raster pages with structured metadata, an explicit reading spine, optional navigation, and optional ComicInfo interoperability metadata.

**KOMA is a name, not an acronym.** It is taken from the Japanese コマ (*koma*), the panel — the smallest unit shared by every form this format carries. It expands to nothing, and MUST NOT be written as an initialism or given a backronym. The name deliberately does not designate any single publishing category, because the format serves all of them equally.

Normative terms **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY** and **OPTIONAL** are used in the sense of BCP 14 (RFC 2119 / RFC 8174). Lowercase occurrences of these words carry no normative weight.

This document specifies version `0.9`. Files declaring `0.9` are development artifacts: see §5.0 before producing or archiving any.

## 1. Package layout

```text
publication.koma
├── mimetype
├── META-INF/
│   └── container.xml
├── ComicInfo.xml                 # optional interoperability file
├── koma/
│   ├── metadata.xml
│   ├── manifest.xml
│   └── nav.xml                   # optional
├── pages/
│   └── ...                       # required raster page resources
└── extensions/                   # optional extension resources
```

Core files are normative. `ComicInfo.xml` is never normative for KOMA.

### 1.1 Scope and non-goals

KOMA is a fixed-page raster format. The following are explicit non-goals of this version:

- reflowable text and embedded font rendering;
- vector or text-layer pages;
- scripting, animation or interactivity of any kind;
- digital rights management or access control;
- storage of reading state, annotations or user data.

Guided panel-level reading is supported only through the optional, safely ignorable region model of §9.4.

## 2. Media type and identification

A KOMA file MUST use the extension `.koma` and the media type `application/vnd.koma+zip`.

The following media types identify the core XML documents. They are literals used inside the package only. They never appear on the wire, they are not intended for IANA registration, and a consumer MUST treat them as fixed strings rather than as resolvable media types.

| Document | Internal media type literal |
| --- | --- |
| `koma/manifest.xml` | `application/vnd.koma.manifest+xml` |
| `koma/metadata.xml` | `application/vnd.koma.metadata+xml` |
| `koma/nav.xml` | `application/vnd.koma.navigation+xml` |

### 2.1 The `mimetype` entry

The root `mimetype` file MUST contain exactly:

```text
application/vnd.koma+zip
```

It is exactly 24 ASCII bytes, with no BOM, whitespace or newline.

The entry MUST be the first physical ZIP entry, MUST use Store (method 0), MUST NOT be encrypted and MUST NOT contain ZIP extra fields. Its local file header MUST begin at byte offset 0 of the file; prepended data such as a self-extracting stub is forbidden. The entry MUST NOT use a data descriptor: the CRC-32 and both size fields MUST be present and correct in the local file header.

These constraints fix the byte layout of the start of the file: the local file header occupies offsets 0–29, the entry name `mimetype` occupies offsets 30–37, and the media type occupies offsets 38–61. A consumer MAY identify a KOMA file by comparing those 24 bytes, without opening the archive.

## 3. ZIP profile

KOMA uses ZIP only. RAR, 7z and other archive syntaxes MUST NOT be used behind the `.koma` extension.

Allowed ZIP compression methods:

- Store (0)
- Deflate (8)

ZIP64 MUST be supported when required. Multipart archives and ZIP encryption are forbidden. Symlinks and other link-like entries are forbidden.

File names MUST use UTF-8, `/` separators and Unicode NFC. Paths are package-root-relative. Absolute paths, `.` segments, `..` segments, backslashes and traversal constructs are forbidden. Logical names MUST be unique after Unicode normalization and case folding.

ZIP timestamps, comments and non-semantic extra fields are not KOMA metadata and MUST NOT affect publication identity (§7.2.1). Deterministic packaging is specified in §14.2.

## 4. XML conventions

### 4.1 Naming

Core KOMA elements use **PascalCase**. Core attributes use lowercase or kebab-case. Normative tokens use lowercase or kebab-case.

All core XML documents MUST be UTF-8. DTDs and external entity resolution are forbidden.

### 4.2 Namespaces

Core namespaces:

- `urn:koma:container`
- `urn:koma:metadata`
- `urn:koma:manifest`
- `urn:koma:navigation`

An element or attribute is **core content** when it belongs to one of these namespaces; unprefixed attributes are core when their owning element is core. Everything else is **foreign content**.

Every core document root MUST carry a `version` attribute (§5). All core documents in one package MUST declare the same value.

### 4.3 Data types

Core attribute and element values use the following lexical types. A value that does not match its type is an error in every processing mode.

| Type | Definition |
| --- | --- |
| `ID` | XML NCName. Unique across the whole `manifest.xml`. Used by `Item/@id`. |
| `IDREF` | NCName matching an existing `Item/@id`. |
| `Path` | Package-root-relative path as defined in §3, matching a ZIP logical name byte-for-byte after NFC normalization. A path is never percent-decoded before matching, and the characters `%`, `?` and `#` MUST NOT appear in it at all, so that a path cannot be mistaken for a URL reference. No leading `/`. |
| `IRI` | Absolute IRI per RFC 3987. Used only for external references. |
| `Integer` | Unsigned decimal, no sign, no leading zeros, no whitespace. |
| `PositiveInteger` | `Integer` greater than 0. Named `PositiveInteger` here and in the schemas. |
| `Boolean` | Exactly `true` or `false`. `1`, `0`, `yes` and `no` are invalid. |
| `Color` | `#` followed by exactly 6 hexadecimal digits. Digits are case-insensitive on input; authoring tools MUST serialize them uppercase. 3- and 8-digit forms are invalid. |
| `Hex` | Lowercase hexadecimal string of the length required by the context. |
| `Date` | ISO 8601 year, year-month, date or dateTime, in the proleptic Gregorian calendar, with a year of four or more digits and no negative years. A `dateTime` MAY carry a timezone offset; the other three forms MUST NOT. |
| `LanguageTag` | Well-formed BCP 47 language tag. |
| `Token` | `[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?`. |
| `TokenList` | One or more `Token` values separated by `;`. No whitespace anywhere, no empty token, no duplicate token. Order is not significant. |
| `Normalized` | Plain text; leading and trailing whitespace are insignificant and MUST be stripped by consumers; internal whitespace sequences are collapsed for comparison but preserved for display. |
| `Decimal01` | Decimal in the closed interval 0–1, with a required leading `0` or `1`, at most 6 fraction digits, `.` as separator. `.5` is invalid, `0.5` is not. |

Two constraints of this table cannot be carried by a schema and are checked at layer 3 of §15: a `TokenList` MUST NOT repeat a token, and a `Normalized` value that is required to be non-empty MUST contain at least one non-whitespace character. The uppercase serialization of `Color` is a canonical-serialization requirement on authoring tools only (§14.1); a reader MUST accept either case, and a validator reports lowercase as a warning, never as an error.

Core element content is plain text unless stated otherwise. CDATA sections, comments and processing instructions carry no meaning and MUST NOT alter interpretation.

The `;` separator is used rather than whitespace because it keeps a single separator convention for lists whose values may later admit spaces. KOMA 0.9 `TokenList` values never contain spaces.

### 4.4 Language of text content

The **document language** of a core document is the value of `xml:lang` on its root element if present, otherwise the value of the first `Language role="content"` in `metadata.xml`.

The language of any text node is the value of the nearest ancestor `xml:lang`, and the document language when there is no such ancestor. An empty `xml:lang=""` means the language is undetermined.

### 4.5 Controlled vocabularies

Many core attributes take values from a controlled vocabulary. Each vocabulary is either **open** or **closed**.

**Closed vocabularies** are exhaustively enumerated and affect rendering or integrity. A value outside the enumeration is always an error, in every processing mode. The closed vocabularies of KOMA 0.9 are:

`Reading/@direction`, `Reading/@spread`, `Item/@page-span`, `Item/@media-type`, `ItemRef/@spread-position`, `PageTarget/@spread-position`, `Content/@color-mode`, `Contributor/@type`, `Checksum/@algorithm`, `Accessibility/@decorative`, `@essential` on extensions, `Resolution/@unit`, `PhysicalFormat/@unit`.

`Accessibility/@decorative` and `@essential` are of the `Boolean` data type of §4.3; they are named here only so that the list of what a reader must reject is complete.

**Open vocabularies** are semantic classification vocabularies. Their value space is the set of **core tokens** listed in this specification plus **private-use tokens**.

A private-use token MUST match `x-[a-z0-9]([a-z0-9-]{0,59}[a-z0-9])?`, which keeps it inside the 63-character ceiling of `Token`. Core tokens MUST NOT begin with `x-`, and no future KOMA version will define a token beginning with `x-`.

Rules for open vocabularies:

- A producer MUST use a core token whenever one applies, and MUST NOT introduce a private-use token that duplicates a core token.
- A reader or validator MUST NOT reject a document because a private-use token is present. It MUST apply the fallback defined in §4.5.1.
- A private-use token MUST NOT be used to satisfy a requirement expressed in terms of a core token. For example, `x-cover` does not satisfy the requirement for exactly one `front-cover` page, and `x-primary` does not satisfy the requirement for exactly one `Title type="main"`.
- A private-use token has no globally defined meaning. Producers MAY document their private-use tokens inside `Metadata/Extensions` using a foreign namespace; such documentation is informational.
- A token that is neither a core token of the vocabulary nor a syntactically valid private-use token is handled per §5.3.

#### 4.5.1 Fallback table

When a reader encounters a token it does not recognize in an open vocabulary, it MUST behave as if the following token had been supplied, or ignore the token where indicated. Ignoring a token never removes the element that carries it.

| Vocabulary | Fallback |
| --- | --- |
| `Identifier/@scheme` | `proprietary` |
| `Title/@type` | `alternative` |
| `Language/@role` | `secondary` |
| `Collection/@type` | `other` |
| `Collection/@relation` | `main` |
| `Name/@type` | `alternative` |
| `Contributor/@roles` (per token) | ignore the token; the contributor is retained |
| `Description/@type` | `note` |
| `Date/@event` | ignore the date |
| `Subject/@type` | `other` |
| `Entity/@type` | `other` |
| `Entity/@role` | ignore the attribute |
| `Content/@original-medium` | `unknown` |
| `Source/@type` | `other` |
| `Digitization/Method` | ignore the element |
| `Digitization/Processing` (per token) | ignore the token |
| `AccessibilityFeature`, `AccessibilityHazard`, `AccessMode` and `AccessModeSufficient` values | ignore the value |
| `ContentWarning/@type` | `other` |
| `Link/@rel` | `other` |
| `Item/@roles` (per token) | `other` |
| `Landmark/@type` | ignore the landmark entry |
| `Region/@type` | `other` |

### 4.6 Extensions

Foreign content MUST use a foreign XML namespace and MUST be placed within an `<Extensions>` element.

KOMA 0.9 defines exactly four extension points:

| Extension point | Scope |
| --- | --- |
| `Metadata/Extensions` | the publication |
| `Manifest/Extensions` | the resource set and reading order |
| `Navigation/Extensions` | navigation |
| `Item/Extensions` | one page resource |

Each is optional, occurs at most once, and MUST be the last child of its parent. An `<Extensions>` element MUST contain at least one foreign element. Core content MUST NOT appear inside `<Extensions>`. `container.xml` has no extension point.

Extension resources MAY be stored below `/extensions/`. See §12.

## 5. Versioning

### 5.0 Major version 0

Major version 0 designates pre-release development versions.

- The compatibility constraints of §5.2 do not apply within major version 0. Any `0.x` version MAY introduce changes that are incompatible with any other `0.x` version and with `1.0`.
- Forward-compatible mode (§5.3) MUST NOT be entered for major version 0. A reader supporting `0.x` MUST reject any document declaring `0.y` where y ≠ x, and MUST report it as an unsupported version.
- A publication declaring a major version of 0 conforms to the pre-release specification of that version only. It is not a KOMA 1.0 publication, and SHOULD NOT be distributed as an archival copy.
- Producers SHOULD be able to re-emit `0.x` content once `1.0` is published, rather than relying on readers to migrate it.
- While no file declaring a given `0.x` version exists outside the repository that defines it, that version MAY be changed incompatibly without changing its number. **Once such a file has been published anywhere**, any further incompatible change MUST take a new number, because a reader supporting `0.x` rejects `0.y` outright and would otherwise be unable to tell the two apart.
- The conformance corpus of §15.1 does not count as published files for the purpose of the preceding rule. Its packages are fixtures rather than publications: they are regenerated whenever the format changes, they are distributed with the specification that defines them, and they are never archival copies.

Version `0.9` will become `1.0` unchanged in substance, or with the changes recorded in the change log, once the criteria of §5.0.1 are met. The serialized value changes from `0.9` to `1.0` at that point and at no other.

#### 5.0.1 Exit criteria for 1.0

The version is raised to `1.0` when all of the following hold:

1. two independent reading system implementations pass the conformance requirements of §16, including the rendering model of §10;
2. a validator implements the four layers of §15 and the version-dependent reporting rules of §5.4;
3. the conformance corpus of §15.1 covers every error listed in §15 and every branch of the pairing algorithm of §10.4, and two independent implementations agree with it;
4. the schemas of §17 are published and agree with this specification;
5. the media type of §2 is registered (§18).

### 5.1 Version numbers

The serialized KOMA version uses `major.minor`, where both parts are `Integer`.

- A major version change MAY introduce incompatible changes.
- Within a major version of 1 or above, a minor version introduces only backward- and forward-compatible additions, under the constraints of §5.2.
- Editorial errata do not change the serialized version.

A KOMA 0.9 implementation MUST support `version="0.9"`.

An implementation's **supported version** is the highest `major.minor` it fully implements.

### 5.2 Constraints on minor versions

To keep §5.3 sound, a future minor version of KOMA within the same major version, where that major version is 1 or above, MUST NOT:

- change the meaning, value space or cardinality of an existing core construct;
- remove or repurpose an existing core construct;
- add a required element or attribute;
- add any core construct whose omission by an older reader would change the meaning of the constructs that reader does retain.

Every construct added by such a minor version MUST be **safely ignorable**: discarding it MUST leave a publication that still renders and reads correctly, only with less information. Any change that is not safely ignorable requires a new major version.

The essential extension mechanism of §12.1 is the single exception, and it is deliberate. An extension marked `essential="true"` changes what a reader that ignores it must do, which is what this section otherwise forbids. It is fenced by §12.1: an essential extension MUST NOT work around a core requirement, the publication MUST remain structurally valid without it, and the consequence of ignoring it is a refusal or a notice rather than a silently wrong rendering. No other construct may claim this exception.

### 5.3 Processing modes

A reader compares the document `version` with its supported version and selects one of three modes.

**Unsupported major.** The document major version differs from the reader's, or either version has a major version of 0 and the two versions are not identical (§5.0). The reader MUST NOT process the document as KOMA of its own major version. It SHOULD report the document as an unsupported version rather than as an invalid publication.

**Strict mode.** Same major version, that major version is 1 or above, and the document minor version is lower than or equal to the reader's supported minor version. In this mode:

- an unknown core element is an error;
- an unknown core attribute is an error;
- a token that is neither a core token of an open vocabulary nor a syntactically valid private-use token is an error;
- closed-vocabulary violations are errors.

Identical `0.x` versions are also processed in strict mode.

**Forward-compatible mode.** Same major version, that major version is 1 or above, and the document minor version is higher than the reader's supported minor version. In this mode:

- the reader MUST NOT reject the document solely because of unknown core elements, unknown core attributes or unknown vocabulary tokens;
- the reader MUST ignore unknown core elements together with their descendants, and MUST ignore unknown core attributes;
- the reader MUST apply §4.5.1 to unknown tokens in open vocabularies, including tokens that are not valid private-use tokens;
- the reader MUST continue to enforce every requirement of its own supported version that it can evaluate on the retained content, including data types, closed vocabularies, structural constraints and security requirements;
- the reader SHOULD surface, once per publication, the fact that the document uses a newer minor version and that some information was ignored.

A reader MAY additionally offer strict processing of newer minor versions as a non-default authoring or diagnostic mode.

### 5.4 Validators

A validator validates against a declared target version.

- When the target version is greater than or equal to the document version, and both share a major version of 1 or above, unknown core content is an error (strict mode).
- When the document version is greater than the target version within the same major version of 1 or above, unknown core content is reported as an informational `unknown-construct` result, not an error, and the validator reports the publication as *valid for the constructs known to this target version*. It MUST NOT report it as conforming to the document's own declared version.
- When either version has a major version of 0 and the two differ, the validator MUST report the document as an unsupported version and MUST NOT report conformance.

## 6. `META-INF/container.xml`

The container locates the root manifest.

```xml
<Container xmlns="urn:koma:container" version="0.9">
  <RootFiles>
    <RootFile full-path="koma/manifest.xml"
              media-type="application/vnd.koma.manifest+xml"/>
  </RootFiles>
</Container>
```

KOMA 0.9 requires exactly one `RootFile`. `@full-path` is a `Path`; `@media-type` MUST be the literal of §2.

## 7. `metadata.xml`

```xml
<Metadata xmlns="urn:koma:metadata" version="0.9" xml:lang="fr">
  ...
</Metadata>
```

### 7.1 Section order and cardinality

Required sections:

- `Identifiers`
- `Titles`
- `Languages`
- `Reading`

Each section listed below MAY occur at most once, and sections MUST appear in this order:

```text
Identifiers
Titles
Languages
Collections?
Contributors?
Descriptions?
Publication?
Subjects?
Entities?
Reading
Content?
Accessibility?
Ratings?
Links?
Rights?
Provenance?
Extensions?
```

A minor version that adds a section defines its position in this order. In forward-compatible mode, a reader ignores unknown sections and MUST NOT treat their position as an ordering violation.

### 7.2 Identifiers

At least one `Identifier` is required and exactly one MUST have `primary="true"`. `@scheme` is required and the element content is `Normalized` and non-empty. Core schemes are `uuid`, `isbn-10`, `isbn-13`, `ean-13`, `issn`, `doi`, `uri`, and `proprietary`. UUID is recommended but not mandatory. `@scheme` is an open vocabulary.

#### 7.2.1 Publication identity

The **publication identity** is the pair (`@scheme`, value) of the primary identifier, compared as exact strings after `Normalized` processing. Two KOMA files with the same publication identity denote the same publication.

The **release identity** is the publication identity combined with `Publication/Date[@event="modified"]`. A producer that changes any core document or page resource MUST update that date if it is present, and SHOULD include it. ZIP-level metadata, compression choices and entry order are not part of either identity.

### 7.3 Titles

Exactly one `Title type="main"` is required. `@type` is required on every `Title`. Core types: `main`, `subtitle`, `original`, `alternative`, `short`, `sort`. `@type` is an open vocabulary. `xml:lang` MAY override the document language.

### 7.4 Languages

At least one `Language role="content"` is required. `@role` is required and the element content is a `LanguageTag`. Core roles: `content`, `original`, `translation`, `secondary`. `@role` is an open vocabulary. Reading direction MUST NOT be inferred from language.

### 7.5 Collections

Collections model membership independently of publication numbering. Core types:

`series`, `subseries`, `cycle`, `story-arc`, `publisher-collection`, `franchise`, `universe`, `anthology`, `other`.

```xml
<Collection type="series" position="3" total="12" relation="main">
  <Name xml:lang="fr">Chroniques du Rivage</Name>
</Collection>
```

`@type` is required. A collection MUST carry at least one `Name` with `Normalized` content, at most one per `xml:lang`; the collection name is not an attribute.

`@position` and `@total` are optional `Normalized` strings, deliberately not integers, so that numbering such as `HS2` or `3.5` survives. `relation="special"` denotes a hors-série/special relation to that collection; default relation is `main`. Core relations: `main`, `special`, `other`. Both `@type` and `@relation` are open vocabularies.

### 7.6 Contributors

A `Contributor` has `type="person|organization"` (closed), one or more structured `Name` values, and a required `roles` attribute of type `TokenList` with at least one token.

Core name types: `name`, `given`, `family`, `middle`, `prefix`, `suffix`, `pseudonym`, `mononym`, `alternative`.

`display-order` and `sort-order` are optional `PositiveInteger` and MAY occur on the same name component. If no display order is supplied, XML name order is the fallback. If no sort order is supplied, display form is the fallback sort key.

Core contributor roles:

`writer`, `script-writer`, `adapter`, `artist`, `penciller`, `inker`, `colorist`, `letterer`, `cover-artist`, `translator`, `editor`, `designer`, `photographer`, `consultant`, `other`.

`@roles` and `Name/@type` are open vocabularies. A contributor whose every role token is unrecognized remains valid and SHOULD be displayed without a role label.

```xml
<Contributor type="person" roles="artist;x-flatter">
  <Name type="given">Claire</Name>
  <Name type="family">Dupont</Name>
</Contributor>
```

### 7.7 Descriptions

`Descriptions` carries free prose about the publication.

```xml
<Descriptions>
  <Description type="summary" xml:lang="fr">...</Description>
  <Description type="note" xml:lang="fr">...</Description>
</Descriptions>
```

Core types (open vocabulary): `summary`, `synopsis`, `blurb`, `note`, `edition-note`, `series-note`, `other`.

At most one `Description` per combination of `type` and `xml:lang`.

### 7.8 Publication

```xml
<Publication>
  <Publisher>...</Publisher>
  <Imprint>...</Imprint>
  <Place>...</Place>
  <Edition number="2">...</Edition>
  <Date event="publication">2026-03</Date>
  <Date event="first-publication">1998</Date>
  <Date event="modified">2026-03-14T10:22:00Z</Date>
  <PhysicalFormat trim-width="170" trim-height="240" unit="mm"/>
</Publication>
```

Children appear in the order shown above.

- `Publisher`, `Imprint`, `Place` and `Edition` are optional, at most one each, `Normalized`, and MAY carry `xml:lang`.
- `Edition/@number` is an optional `PositiveInteger`.
- `Date` MAY occur any number of times, but at most once per `event` value. Values are `Date`. No separate precision attribute is stored; precision is carried by the lexical form.
- `PhysicalFormat` is optional and at most once. `@trim-width` and `@trim-height` are `PositiveInteger`, `@unit` is `mm` only in KOMA 0.9. It describes the source print format and MUST NOT affect rendering; a reading system MAY use it for physical-size simulation.

Core date events (open vocabulary): `publication`, `first-publication`, `creation`, `digitization`, `modified`.

### 7.9 Subjects

```xml
<Subjects>
  <Subject type="genre" xml:lang="fr">Science-fiction</Subject>
  <Subject type="genre" scheme="bisac" code="CGN004050"/>
  <Subject type="keyword" xml:lang="fr">post-apocalyptique</Subject>
</Subjects>
```

`Subject` has an optional `type`, optional `scheme`, optional `code`, and optional `Normalized` content. At least one of text content or `@code` MUST be present. When `@code` is present, `@scheme` MUST be present.

Core subject types (open vocabulary): `genre`, `theme`, `keyword`, `setting`, `time-period`, `audience`, `other`. Default when `@type` is absent is `keyword`.

`@scheme` is an uncontrolled string identifying an external classification system; KOMA 0.9 defines no scheme registry.

### 7.10 Entities

`Entities` lists named entities appearing in the work. It is descriptive metadata, not navigation, and MUST NOT be used to locate content.

```xml
<Entity type="character" role="protagonist">
  <Name>Alix</Name>
  <Name type="alternative" xml:lang="ja">アリックス</Name>
</Entity>
```

Each `Entity` requires at least one `Name` with `Normalized` content. `Name` MAY carry `xml:lang` and an optional `type` using the vocabulary of §7.6.

Core entity types (open vocabulary): `character`, `team`, `organization`, `location`, `vehicle`, `object`, `event`, `other`.

Core entity roles (open vocabulary): `protagonist`, `antagonist`, `supporting`, `cameo`, `narrator`. `@role` is optional and meaningful only for `type="character"`; readers MUST ignore it on other types.

### 7.11 Reading

`Reading` is required:

```xml
<Reading direction="rtl" spread="auto"/>
```

`direction` is REQUIRED: `ltr|rtl`. There is no default, because no default is safe for a format that carries both Western and Japanese reading orders.

`spread` is OPTIONAL: `none|auto|force`, default `auto`.

Both vocabularies are closed. Their rendering semantics are normative and specified in §10.

### 7.12 Content

```xml
<Content color-mode="monochrome" original-medium="print"/>
```

`@color-mode` (closed): `monochrome|color|mixed|unknown`. Default when absent is `unknown`. It is descriptive and MUST NOT trigger any automatic colour transformation.

`@original-medium` (open): `print`, `digital`, `webtoon`, `mixed`, `unknown`. Default when absent is `unknown`. Informational; it MUST NOT alter `direction`, `spread` or spread pairing.

### 7.13 Accessibility

Publication-level accessibility metadata.

```xml
<Accessibility>
  <AccessMode>visual</AccessMode>
  <AccessModeSufficient>visual</AccessModeSufficient>
  <AccessModeSufficient>textual</AccessModeSufficient>
  <AccessibilityFeature>alternative-text</AccessibilityFeature>
  <AccessibilityHazard>no-flashing-hazard</AccessibilityHazard>
  <AccessibilitySummary xml:lang="fr">...</AccessibilitySummary>
  <ConformsTo identifier="EPUB Accessibility 1.1 - WCAG 2.1 Level AA"
              href="https://www.w3.org/TR/epub-a11y-11/"/>
  <Certification certified-by="..." credential="..." report="https://..."/>
</Accessibility>
```

Children appear in the order shown above.

- `AccessMode`: one or more. Core values (open): `visual`, `textual`, `auditory`, `tactile`.
- `AccessModeSufficient`: zero or more; each element is a `TokenList` of access modes sufficient on their own to consume the publication.
- `AccessibilityFeature`: zero or more. Core values (open): `alternative-text`, `long-description`, `reading-order`, `structural-navigation`, `page-navigation`, `table-of-contents`, `high-contrast-display`, `none`.
- `AccessibilityHazard`: zero or more. Core values (open): `flashing`, `no-flashing-hazard`, `motion-simulation`, `no-motion-simulation-hazard`, `sound`, `no-sound-hazard`, `none`, `unknown`. A publication MUST NOT declare both a hazard and its corresponding `no-…-hazard` value.
- `AccessibilitySummary`: at most one per `xml:lang`, `Normalized`.
- `ConformsTo`: zero or more; `@identifier` required `Normalized`, `@href` optional `IRI`.
- `Certification`: at most one. `@certified-by` and `@credential` are optional `Normalized` strings, `@report` is an optional `IRI`. All three are optional, but an empty `Certification` asserts nothing and SHOULD be omitted.

These vocabularies are drawn from schema.org and EPUB Accessibility but are spelled in kebab-case to satisfy the `Token` type of §4.3. A tool exporting to schema.org or ONIX MUST convert them to the camelCase spelling used there: `alternative-text` becomes `alternativeText`, `no-flashing-hazard` becomes `noFlashingHazard`, and so on.

Because KOMA pages are raster images, a publication SHOULD declare `Accessibility` with at least one `AccessibilitySummary` and one `AccessibilityHazard`, and SHOULD provide `Item/Accessibility/AlternativeText` (§8.7) for every information-bearing page. Their absence is a validation warning (§15).

Declared hazards MUST be consistent with `ContentWarning` values: declaring `no-flashing-hazard` together with a `flashing-images` content warning is an error.

### 7.14 Ratings

```xml
<Ratings>
  <Rating scheme="cero" value="C" region="JP"/>
  <ContentWarning type="flashing-images" xml:lang="fr">...</ContentWarning>
</Ratings>
```

`Rating` elements precede `ContentWarning` elements. `Ratings` MUST NOT be empty.

`Rating` requires `@scheme` and `@value`, both uncontrolled strings, and MAY carry `@region` as an ISO 3166-1 alpha-2 code. KOMA 0.9 defines no rating scheme registry and does not compare ratings across schemes. Ratings are informational; KOMA defines no enforcement behaviour.

`ContentWarning` requires `@type`, MAY carry `xml:lang`, and MAY have `Normalized` content. Core warning types (open vocabulary): `violence`, `gore`, `sexual-content`, `nudity`, `language`, `drug-use`, `self-harm`, `flashing-images`, `other`.

A reading system that offers photosensitivity safeguards SHOULD honour `flashing-images` and `AccessibilityHazard` value `flashing`.

### 7.15 Links

```xml
<Links>
  <Link rel="publisher" href="https://example.org/"/>
  <Link rel="license" href="https://example.org/license"/>
</Links>
```

`Link` requires `@rel` and `@href` (`IRI`), and MAY carry `@media-type`, `xml:lang` and `Normalized` content used as a label.

A `Link` MUST NOT reference a resource inside the package. Core reading MUST NOT depend on link resolution, and a reading system MUST NOT dereference a link without explicit user action.

Core relations (open vocabulary): `homepage`, `publisher`, `author`, `series`, `purchase`, `record`, `errata`, `license`, `source`, `related-publication`, `other`.

### 7.16 Rights

```xml
<Rights>
  <Copyright xml:lang="fr">© 2026 Éditions Exemple</Copyright>
  <License identifier="CC-BY-SA-4.0" href="https://example.org/cc-by-sa-4.0"/>
  <Statement xml:lang="fr">...</Statement>
</Rights>
```

- `Copyright`: at most one per `xml:lang`, `Normalized`.
- `License`: any number; `@identifier` is an uncontrolled string, SPDX identifiers are RECOMMENDED where applicable; `@href` is an optional `IRI`.
- `Statement`: at most one per `xml:lang`, `Normalized`.

`Rights` MUST NOT be empty. `Rights` is declarative. KOMA defines no DRM, no encryption and no technical enforcement mechanism, and a conforming reader MUST NOT infer any access restriction from this section.

### 7.17 Provenance

`Provenance` records where the pages came from. It is informational: it MUST NOT override core publication metadata, MUST NOT participate in publication identity (§7.2.1), and MUST NOT affect rendering.

```xml
<Provenance>
  <Source type="print">
    <Identifier scheme="isbn-10">2123456803</Identifier>
    <Publisher>Éditions Exemple</Publisher>
    <Edition>Première édition</Edition>
    <Date event="publication">1998</Date>
    <Holding institution="BnF" shelfmark="4-CG-1234"/>
  </Source>
  <Digitization>
    <Agent>Atelier Numérique</Agent>
    <Date>2024-05-02</Date>
    <Method>flatbed-scan</Method>
    <Resolution value="600" unit="dpi"/>
    <Equipment>Epson Expression 12000XL</Equipment>
    <Processing>deskew;despeckle</Processing>
  </Digitization>
  <Note xml:lang="fr">Exemplaire relié, dos recollé.</Note>
</Provenance>
```

`Source` describes the object that was reproduced. It occurs at most once. `@type` is required, from the open vocabulary `print`, `digital`, `microform`, `original-artwork`, `periodical`, `other`. Its children, in this order and each optional unless noted:

- `Identifier`: zero or more, `@scheme` required, using the vocabulary of §7.2. These identify the *source*, not this publication, and MUST NOT be read as KOMA identifiers.
- `Publisher`, `Edition`: at most one each, `Normalized`, `xml:lang` allowed.
- `Date`: zero or more, at most one per `@event`, using the vocabulary of §7.8.
- `Holding`: at most one; `@institution` required, `@shelfmark` optional. It names the physical copy that was used.

`Digitization` describes how the raster pages were produced. It occurs at most once. Its children, in this order, all optional and at most one each:

- `Agent`: who performed the digitization.
- `Date`: when, as a `Date`.
- `Method`: open vocabulary — `flatbed-scan`, `sheet-fed-scan`, `overhead-scan`, `photography`, `born-digital`, `other`.
- `Resolution`: `@value` is a `PositiveInteger`, `@unit` is closed and takes `dpi` or `ppcm`. It records the capture resolution, which is not necessarily the stored resolution.
- `Equipment`: free text.
- `Processing`: a `TokenList` of transformations applied after capture. Open vocabulary — `deskew`, `despeckle`, `crop`, `level-adjust`, `colour-correction`, `denoise`, `upscale`, `recompression`, `other`.

`Note` carries free prose, zero or more, at most one per `xml:lang`. `Provenance` MUST NOT be empty.

Provenance frequently contains information about people and institutions. Producers SHOULD NOT record the name of a private individual in `Agent` or `Holding` without their agreement.

## 8. `manifest.xml`

The manifest declares all raster pages and the canonical reading order.

```xml
<Manifest xmlns="urn:koma:manifest"
          xmlns:demo="https://example.org/ns/demo"
          version="0.9"
          metadata="koma/metadata.xml"
          navigation="koma/nav.xml">
  <Resources>
    <Item id="p001" href="pages/001.jpg" media-type="image/jpeg"
          width="1600" height="2400" roles="front-cover">
      <Checksum algorithm="sha-256">e3b0c442...b7852b855</Checksum>
      <Accessibility decorative="false">
        <AlternativeText xml:lang="fr">Couverture : ...</AlternativeText>
      </Accessibility>
    </Item>
    <Item id="p002" href="pages/002.png" media-type="image/png"
          width="1600" height="2400" roles="story"/>
    <Item id="p003" href="pages/003.webp" media-type="image/webp"
          width="3200" height="2400" roles="story" page-span="2"/>
  </Resources>
  <Spine>
    <ItemRef item="p001"/>
    <ItemRef item="p002" spread-position="right"/>
    <ItemRef item="p003"/>
  </Spine>
  <Extensions>
    <demo:build-id>2026-03-14T10:22:00Z</demo:build-id>
  </Extensions>
</Manifest>
```

`Manifest` contains `Resources`, then `Spine`, then an optional `Extensions`, in that order. `@metadata` is REQUIRED and `@navigation` is OPTIONAL; both are `Path`. `navigation` is omitted when `nav.xml` is absent.

### 8.1 Items

Every raster image under `/pages/` MUST be declared exactly once. Every KOMA 0.9 `Item` MUST reference an image below `/pages/`.

Resources below `/extensions/` are not declared in the manifest; an extension that requires assets is responsible for referencing them from its own foreign-namespace content (§12).

Required attributes:

- `id` (`ID`)
- `href` (`Path`)
- `media-type` (closed vocabulary)
- `width` (`PositiveInteger`)
- `height` (`PositiveInteger`)

Optional attributes:

- `roles` (`TokenList`)
- `page-span` (closed vocabulary, §8.5)
- `background-color` (`Color`)

`Item` children, in this order, each optional and at most once: `Checksum` (§8.6), `Accessibility` (§8.7), `Extensions` (§4.6).

Supported page media types (closed):

- `image/jpeg`
- `image/png`
- `image/webp`

`@media-type` MUST match the actual byte signature of the resource.

Pages MUST be static. Animated WebP is invalid. RGB and grayscale are supported; CMYK is outside the base profile. Up to 8 bits/channel is mandatory for readers; 16-bit PNG is permitted and MAY be rendered at lower precision.

#### 8.1.1 Recommended page naming

File names carry no meaning in KOMA: the spine is the only reading order (§8.8), and a reading system MUST NOT derive order, pagination or roles from a name. The following is therefore a recommendation for producers and the basis of the naming warning of §15, not a constraint on readers.

Page resources SHOULD be named `pages/NNN.ext`, where `NNN` is a zero-padded decimal counter that ascends in spine order, starts at 1, and is at least three digits wide, widening as needed for the page count. `ext` SHOULD be `.jpg`, `.png` or `.webp` according to the media type.

A producer that renumbers pages from a source archive SHOULD state the relationship somewhere the user can see it, because a numbering that starts at 1 does not line up with formats that count from 0. `ComicInfo.xml` in particular numbers its `Page/@Image` from 0, so when a ComicInfo projection travels with the package (§11), `Image="0"` denotes `pages/001` and `Image="N"` denotes page N+1.

### 8.2 Orientation

`width` and `height` are exact final raster dimensions after orientation normalization. EXIF orientation MUST be physically applied by the producer, and any residual EXIF orientation tag MUST be `1` or absent.

A reading system MUST ignore EXIF orientation entirely and MUST render pixels as stored. This prevents double rotation.

### 8.3 Colour management

- A page resource MAY embed an ICC profile (JPEG `APP2`, PNG `iCCP`, WebP `ICCP`).
- When a profile is embedded, a reading system SHOULD apply it. When it cannot, it MUST fall back to treating the data as sRGB and MUST NOT fail.
- When no profile is embedded, the colour space is sRGB (IEC 61966-2-1) for RGB data, and the sRGB transfer function for grayscale data. PNG `sRGB`, `gAMA` and `cHRM` chunks are honoured in the absence of `iCCP`.
- Producers MUST NOT remove an embedded ICC profile when stripping metadata under §13. Wide-gamut profiles are permitted.
- `Content/@color-mode` is descriptive and MUST NOT drive any conversion.

### 8.4 Roles

Core page roles (open vocabulary, fallback `other`):

`front-cover`, `inner-cover`, `title-page`, `table-of-contents`, `recap`, `story`, `interlude`, `illustration`, `advertisement`, `editorial`, `letters`, `preview`, `credits`, `bonus`, `blank`, `back-cover`, `other`.

Exactly one `Item` in the package MUST carry the core token `front-cover` in its `roles`. A private-use token MUST NOT be used to designate the front cover. That item MUST appear in the spine and SHOULD be its first entry.

### 8.5 Page span

`page-span` is `1|2` (closed); default is `1`. A value of `2` means one raster image physically contains two pages.

### 8.6 Integrity

An item MAY contain a SHA-256 checksum:

```xml
<Checksum algorithm="sha-256">...</Checksum>
```

`@algorithm` is closed and its only KOMA 0.9 value is `sha-256`. The digest is a 64-character `Hex` value over the exact uncompressed image bytes.

### 8.7 Accessibility

An item MAY contain page-level accessibility information:

```xml
<Accessibility decorative="false">
  <AlternativeText xml:lang="fr">...</AlternativeText>
  <Description xml:lang="fr">...</Description>
</Accessibility>
```

`AlternativeText` is a concise textual alternative, at most one per `xml:lang`. `Description` is an optional extended description, at most one per `xml:lang`. A purely decorative page MAY set `decorative="true"`; in that case `AlternativeText` MUST NOT be present.

### 8.8 Spine

The `Spine` is the only normative reading order. File names and resource declaration order do not define reading order.

Each `ItemRef/@item` is an `IDREF`. An item MUST NOT occur more than once in the spine. Resources outside the spine are allowed but MUST be treated as non-reading resources and generate a validation warning.

`ItemRef/@spread-position`: `auto|left|right|center` (closed); default `auto`. `left` and `right` are physical screen positions, independent of `direction`. A `page-span="2"` item MUST NOT use `left` or `right`.

## 9. `nav.xml`

`nav.xml` is optional.

```xml
<Navigation xmlns="urn:koma:navigation" version="0.9" xml:lang="fr">
  <TableOfContents>...</TableOfContents>
  <PageList>...</PageList>
  <Landmarks>...</Landmarks>
  <Regions>...</Regions>
  <Extensions>...</Extensions>
</Navigation>
```

Sections MUST appear in the order above. Each occurs at most once, and at least one of `TableOfContents`, `PageList`, `Landmarks` and `Regions` MUST be present; an `Extensions` element alone does not satisfy this.

All navigation targets are carried by an `item` attribute of type `IDREF`. They reference `Item/@id`, never image paths, and MUST target items in the spine.

### 9.1 Table of contents

```xml
<TableOfContents>
  <Entry item="p002">
    <Label xml:lang="fr">Chapitre 1</Label>
    <Label xml:lang="en">Chapter 1</Label>
    <Entry item="p012">
      <Label xml:lang="fr">La traversée</Label>
    </Entry>
  </Entry>
</TableOfContents>
```

`TableOfContents` contains one or more `Entry`. Each `Entry` requires `@item` and at least one `Label`, and MAY contain nested `Entry` children, which follow its labels. `Label` carries `Normalized` content and an optional `xml:lang`, at most one per language. Nesting depth is not limited by this specification, but is bounded by §13.1.

### 9.2 Page list

```xml
<PageList>
  <PageTarget item="p012" label="12"/>
  <PageTarget item="p013" label="13" spread-position="right"/>
  <PageTarget item="p013" label="14" spread-position="left"/>
</PageList>
```

`PageList` contains one or more `PageTarget`, each an empty element requiring `@item` and `@label`. `@label` is a `Normalized` string, not an integer, so that `iv`, `12bis` and `A-3` are expressible.

`@spread-position` is OPTIONAL and has no default: its absence means the label denotes the whole resource, not one half of it. Its value space is `left|right` only, unlike `ItemRef/@spread-position` (§8.8), which also admits `auto` and `center`; the two attributes share a name but not a vocabulary.

For `page-span="2"`, two logical pages MAY target the same resource using `@spread-position="left|right"` (closed). Two `PageTarget` elements MUST NOT share both the same item and the same `spread-position`, and `@spread-position` MUST NOT be used on an item whose `page-span` is 1.

### 9.3 Landmarks

```xml
<Landmarks>
  <Landmark type="front-cover" item="p001"/>
  <Landmark type="body-start" item="p005">
    <Label xml:lang="fr">Début du récit</Label>
  </Landmark>
</Landmarks>
```

`Landmarks` contains one or more `Landmark`. Each requires `@type` and `@item` and MAY carry `Label` children, at most one per `xml:lang`.

Core landmark types (open vocabulary; an unrecognized type causes the landmark entry to be ignored):

`front-cover`, `inner-cover`, `title-page`, `table-of-contents`, `body-start`, `story-start`, `credits`, `glossary`, `appendix`, `bonus`, `preview`, `back-cover`.

Landmarks are flat, not hierarchical. At most one landmark per type.

### 9.4 Regions

`Regions` provides optional panel-level guided reading.

```xml
<Regions>
  <RegionSequence item="p012">
    <Region type="panel" x="0.04" y="0.03" width="0.44" height="0.30">
      <Label xml:lang="fr">...</Label>
    </Region>
    <Region type="panel" x="0.52" y="0.03" width="0.44" height="0.30"/>
  </RegionSequence>
</Regions>
```

- `Regions` contains one or more `RegionSequence`, each containing one or more `Region`.
- At most one `RegionSequence` per item; `@item` is an `IDREF` to a spine item.
- `Region/@x`, `@y`, `@width` and `@height` are required; `@type` is optional; `Label` children are optional, at most one per `xml:lang`.
- `@x`, `@y`, `@width`, `@height` are `Decimal01`, expressed as fractions of the item's stored raster dimensions after orientation normalization. `x + width` and `y + height` MUST NOT exceed 1. The origin is the top-left corner.
- Document order inside a `RegionSequence` is the guided reading order and takes precedence over `Reading/@direction` for that item.
- `Region/@type` is an open vocabulary; core values: `panel`, `group`, `inset`, `caption`, `other`.
- Regions MAY overlap and need not cover the whole page.
- `Label` is optional, at most one per `xml:lang`.

Regions are safely ignorable. A reading system that does not implement guided reading MUST still render full pages in spine order, and a publication MUST NOT depend on regions for its content to be readable.

### 9.5 Excluded state

Personal bookmarks, reading progress, annotations and last-read state MUST NOT be stored in core KOMA navigation.

## 10. Rendering model

This section is normative. Its purpose is to make two conforming reading systems produce the same pagination for the same publication.

### 10.1 Display mode

A reading system displays either one item at a time (**single mode**) or two items side by side (**spread mode**).

- `spread="none"`: the reading system MUST use single mode.
- `spread="force"`: the reading system MUST use spread mode whenever the viewport can present two items side by side, and MUST fall back to single mode otherwise.
- `spread="auto"`: the reading system chooses, and SHOULD use spread mode when the viewport is wider than tall.

In single mode, `spread-position` has no effect and items are displayed one by one in spine order. A reading system MAY offer to split a `page-span="2"` item into two halves as a user option; this MUST NOT be the default and MUST NOT alter the spine.

### 10.2 Sides

The **leading side** is the physical side where reading begins: `left` when `direction="ltr"`, `right` when `direction="rtl"`. The **trailing side** is the other one.

### 10.3 Effective spread position

For each spine entry, the effective position is determined as follows, in order:

1. `page-span="2"` → **full**.
2. `spread-position="center"` → **full**.
3. `spread-position="left"` or `"right"` → that physical side, **fixed**.
4. `spread-position="auto"` and the item's `roles` contain the core token `front-cover` → **full**.
5. Otherwise → **flow**.

Rule 4 makes the usual single-cover presentation the default without producer action; a producer that wants the cover paired MUST set an explicit `left` or `right`.

### 10.4 Pairing algorithm

In spread mode, a reading system MUST produce the sequence of displayed spreads with the following algorithm. `buffer` holds at most one leading-side item and one trailing-side item.

```text
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
```

**Spine-order invariant.** Within an emitted spread, an item that comes earlier in the spine MUST NOT be placed on the side that is read after an item that comes later. This is what the first two lines of the flow branch enforce: the buffer is emitted rather than back-filled whenever its trailing half is already occupied. Without this rule a page pinned with `spread-position` would pull the page that follows it onto the side read first, and the spine would no longer be the reading order §8.8 says it is.

An emitted spread with one occupied half is rendered with the other half empty. The empty half MUST be filled with the `background-color` of the accompanying item, or `#FFFFFF` when that item declares none.

A reading system MAY offer a user control that shifts pairing by one position. It MUST NOT be enabled by default and MUST NOT alter the spine.

### 10.5 Compositing

Transparency is allowed. The default compositing background is `#FFFFFF`; `background-color="#RRGGBB"` on an item overrides it for that item.

### 10.6 Worked example

`direction="rtl"`, spine: `c` (`roles="front-cover"`), `p1`, `p2`, `d` (`page-span="2"`), `p3`.

Leading side is `right`. `c` is full by rule 4 → spread 1 is `c` alone. `p1` takes the right half, `p2` the left half → spread 2. `d` is full → spread 3. Nothing follows `p3`, so it occupies the right half of spread 4 with an empty left half.

## 11. ComicInfo interoperability

`/ComicInfo.xml` is optional and MUST remain valid according to the ComicInfo schema used by the producer. It is a compatibility projection only; KOMA XML wins on conflict. The mapping of Annex A is the RECOMMENDED projection.

The `.koma` extension itself may not be recognized by legacy CBZ/CBR applications. A KOMA tool SHOULD therefore provide CBZ export containing the page images and generated `ComicInfo.xml` when legacy container interoperability is required.

KOMA-to-ComicInfo conversion is intentionally lossy when KOMA has richer structured data. Private-use tokens (§4.5) have no ComicInfo equivalent and are dropped by the projection.

## 12. Extensions

Extension XML MUST use a foreign namespace and occur inside one of the four `<Extensions>` elements of §4.6. Each direct child of `<Extensions>` is one extension.

Unknown **core** content is not an extension point: it is handled by the version rules of §5.3, and unknown core elements MUST NOT be used as a substitute for a foreign-namespace extension.

### 12.1 Essential extensions

A direct child of `<Extensions>` MAY carry the attribute `essential` in the `urn:koma:metadata` namespace, of type `Boolean`. Default is `false`.

- `essential="false"`: a reader that does not understand the extension MUST ignore it and MUST continue to present the publication.
- `essential="true"`: the producer asserts that the publication cannot be presented faithfully without the extension. A reader that does not understand the extension MUST NOT present the publication as complete; it MUST either refuse to open it or present it with a persistent notice that essential content is missing.

The attribute is allowed on the direct children of any of the four extension points. An extension declared essential inside `Item/Extensions` is essential for that page only; a reading system MAY present the rest of the publication and mark that page as incomplete.

An essential extension MUST NOT be used to work around a core requirement, and a publication MUST remain structurally valid when its essential extensions are ignored.

### 12.2 Extension resources

External extension assets MAY be stored only below `/extensions/`. Core reading MUST NOT depend on unknown extension assets. Extension assets are not manifest items (§8.1) and carry no core integrity or accessibility metadata.

## 13. Security

A reader MUST reject path traversal, absolute paths, duplicate logical ZIP entries, encrypted entries and link entries.

XML parsers MUST disable DTD processing and external entity resolution.

KOMA contains no executable content. A reading system MUST NOT execute scripts, MUST NOT process SVG or HTML as page content, and MUST NOT perform network access to render a publication.

Embedded image metadata is non-normative. Producers SHOULD remove privacy-sensitive EXIF/XMP data that is not required for rendering, while preserving ICC profiles (§8.3).

### 13.1 Resource limits

A reader MUST bound resource use. The following defaults are RECOMMENDED and SHOULD be configurable:

- total uncompressed size at most 4 GiB, and at most 100 times the archive size;
- per-entry compression ratio above 100:1 treated as suspicious and rejected unless the entry is within the absolute limits;
- at most 10 000 ZIP entries;
- at most 100 megapixels per page resource, and at most 65 535 pixels per side;
- at most 16 MiB per core XML document;
- XML element nesting depth at most 100.

Exceeding a limit MUST result in a controlled failure, never in unbounded allocation.

Forward-compatible processing (§5.3) MUST NOT relax any requirement in this section.

## 14. Canonical serialization and packaging

### 14.1 XML canonical rules

An authoring tool MUST emit core documents that satisfy all of the following:

- UTF-8 without BOM;
- an XML declaration `<?xml version="1.0" encoding="UTF-8"?>`;
- LF line endings;
- no DTD, no external entities, no CDATA sections, no processing instructions;
- namespace declarations only on the root element, except for foreign content inside `Extensions`;
- attributes serialized in the order given by this specification, with `id` first when present;
- no insignificant whitespace inside elements that carry `Normalized` text.

The `version` pseudo-attribute of the XML declaration refers to the XML specification and is unrelated to the KOMA version of §5.

These rules exist so that two tools producing the same logical publication produce byte-identical core documents.

### 14.2 Reproducible packaging

An authoring tool SHOULD produce reproducible archives:

- `mimetype` first, stored, per §2.1;
- remaining entries sorted by logical name using byte-wise comparison of the UTF-8 NFC form;
- a fixed ZIP timestamp;
- no ZIP comments and no non-semantic extra fields.

Reproducible packaging is not required for conformance, and its absence MUST NOT affect publication identity (§7.2.1).

## 15. Validation model

A conforming validator performs four layers:

1. **Container validation** — ZIP profile, mimetype bytes and offset, paths, uniqueness, resource limits.
2. **XML validation** — schemas, data types and lexical constraints, evaluated in the mode selected by §5.4.
3. **Cross-document validation** — references, unique primary metadata, cover, navigation targets, spine constraints, region targets, accessibility consistency.
4. **Resource validation** — actual MIME signatures, dimensions, animation, EXIF orientation residue, checksums, image and colour profile.

Examples of errors:

- wrong `mimetype` content, position, method or local header offset;
- missing required XML;
- inconsistent `version` across core documents;
- unknown KOMA core element or attribute, in strict mode (§5.3);
- value violating a data type of §4.3, in any mode;
- value outside a closed vocabulary, in any mode;
- token in an open vocabulary that is neither a core token nor a valid private-use token, in strict mode;
- private-use token used to satisfy a core-token requirement;
- metadata sections out of canonical order or repeated;
- missing or duplicate primary identifier;
- missing or duplicate main title;
- no content language;
- no front cover or multiple front covers;
- front cover absent from the spine;
- missing spine target;
- item occurring more than once in the spine;
- navigation or region target outside the spine;
- more than one `RegionSequence` for the same item, or region coordinates outside the unit square;
- wrong image dimensions or media type;
- residual EXIF orientation other than `1`;
- `page-span="2"` with `spread-position="left|right"`;
- animated page resource;
- contradictory accessibility hazard and content warning;
- `decorative="true"` together with `AlternativeText`;
- navigation sections out of order, or `nav.xml` containing only `Extensions`;
- `PageTarget/@spread-position` on an item whose `page-span` is 1;
- two `PageTarget` elements sharing the same item and `spread-position`;
- more than one landmark of the same type;
- `Extensions` containing core content, or occurring outside the four points of §4.6;
- `Collection` without a `Name`;
- duplicate token within a `TokenList`;
- un-namespaced element inside `Extensions`;
- `Subject` with neither text content nor `@code`, or with `@code` and no `@scheme`;
- a spread that would place an earlier spine item on the side read after a later one (§10.4), for a reading system;
- failed checksum;
- unsupported essential extension, for a reading system.

Examples of warnings:

- page resource not referenced by the spine;
- no navigation document;
- no publication-level `Accessibility` section;
- no accessibility description for information-bearing pages;
- front cover present in the spine but not first;
- ComicInfo projection inconsistent with KOMA;
- page naming that departs from §8.1.1;
- private-use tokens present in the publication;
- core documents not in canonical serialization;
- `Color` value serialized in lowercase.

Informational results:

- unknown core construct ignored while validating a newer minor version (§5.4);
- publication declares a pre-release version (§5.0).

### 15.1 Conformance corpus

A conformance corpus accompanies this specification:

```text
corpus/
├── expected.json          # the outcome each package must produce
├── valid-*.koma
├── L1-*.koma              # container-layer failures
├── L3-*.koma              # cross-document failures
└── L4-*.koma              # resource-layer failures
```

Each package differs from `valid-minimal.koma` in exactly one respect, and `expected.json` states, for each, whether a conforming validator MUST report it as valid, as carrying a named warning, or as carrying a named error. The corpus is normative by example: a validator that disagrees with `expected.json` does not conform, and a disagreement that this specification does not settle is an erratum.

The corpus is not exhaustive. It covers the failures listed in §15 that can be produced by mutating a single package, and it does not attempt to cover the layer 2 failures, which are exercised directly against the schemas of §17.

The pairing fixtures of §10.4 are distributed with the corpus. Their expected output is written from the specification text by hand rather than produced by an implementation, so that an implementation bug cannot silently redefine the pagination.

## 16. Conformance classes

Conformance in this document is conformance to KOMA 0.9. It does not imply conformance to KOMA 1.0, whose text may still change (§5.0).

### KOMA Publication

A publication conforms when it satisfies all MUST/MUST NOT requirements in this specification.

### KOMA Reading System

A conforming reading system MUST:

- open the KOMA ZIP profile including ZIP64;
- support JPEG, PNG and WebP static pages;
- parse all core XML documents;
- apply the version processing rules of §5.0 and §5.3, including forward-compatible handling of newer minor versions once the major version reaches 1;
- apply the open-vocabulary fallbacks of §4.5.1 and reject closed-vocabulary violations;
- follow the spine as canonical reading order;
- implement the rendering model of §10, including the pairing algorithm;
- ignore EXIF orientation and apply the colour rules of §8.3;
- support navigation when provided;
- safely ignore foreign extensions, and honour §12.1 for essential ones;
- enforce security requirements and resource limits.

A conforming reading system MAY omit guided region navigation (§9.4).

### KOMA Authoring Tool

A conforming authoring tool MUST emit conforming publications, MUST apply the canonical serialization rules of §14.1, and SHOULD normalize image orientation and paths. It SHOULD produce reproducible archives and SHOULD warn when a private-use token is emitted where a core token exists.

### KOMA Validator

A conforming validator MUST implement the four layers of §15 and the version-dependent reporting rules of §5.4, and MUST distinguish errors, warnings and informational results.

## 17. Schemas

Normative schemas for the four core documents are published alongside this specification in RELAX NG compact syntax:

`koma-container-0.9.rnc`, `koma-metadata-0.9.rnc`, `koma-manifest-0.9.rnc`, `koma-navigation-0.9.rnc`.

The schemas constitute layer 2 of §15 and nothing more. They express element structure, child order, cardinality, required and optional attributes, the data types of §4.3 and the closed vocabularies of §4.5. Because RELAX NG validates one document at a time, they cannot express:

- open-vocabulary membership — a token is checked for lexical form only, so `story` and `x-anything` are equally acceptable to the schema and the distinction of §4.5 is made at layer 3;
- uniqueness and singleton rules — exactly one primary identifier, exactly one main title, exactly one front cover, one landmark per type, one `Description` per type and language, and the absence of duplicate tokens within a `TokenList`;
- that foreign content actually carries a foreign namespace: the schemas exclude the four core namespaces at every depth inside `Extensions`, but RELAX NG compact as emitted by the reference toolchain cannot also exclude the no-namespace name class, so an un-namespaced element inside `Extensions` is rejected at layer 3 (§4.6);
- the uppercase serialization of `Color`, which is an authoring-tool requirement and a warning, never an error;
- referential integrity — `IDREF` is validated as an NCName, not as an existing `Item/@id` in the spine;
- constraints spanning documents, such as navigation targets or the consistency of `AccessibilityHazard` with `ContentWarning`;
- byte-level and resource facts — ZIP layout, path uniqueness after case folding, image signatures, dimensions, EXIF residue and checksums.

A validator that runs the schemas alone is not a conforming KOMA validator.

Where a schema and this specification disagree, this specification prevails and the discrepancy is an erratum.

## 18. Media type registration

`application/vnd.koma+zip` is the media type for KOMA. It is a vendor-tree name under RFC 6838 §3.2, submitted directly to IANA and subject to Expert Review; no RFC is required. The `+zip` structured syntax suffix is already registered by RFC 6839 and needs no separate action.

Registration in the vendor tree implies no endorsement, approval or recommendation by the IETF or IANA.

Until registration completes, the name is used as specified here and MUST NOT be spelled with an `x-` prefix, which is deprecated by RFC 6648.

The internal literals of §2 are not submitted for registration. They exist only to identify core documents inside the package.

Should KOMA later be adopted by a recognized standards organization and re-registered in the standards tree, the resulting name would differ and the change would be a major version change under §5.1.

---

## Annex A — ComicInfo projection (informative)

| ComicInfo field | KOMA source |
| --- | --- |
| `Series` | `Collection[@type="series"]/Name` |
| `Number` | `Collection[@type="series"]/@position` |
| `Count` | `Collection[@type="series"]/@total` |
| `Title` | `Title[@type="main"]` |
| `Summary` | `Description[@type="summary"]` |
| `Notes` | `Description[@type="note"]` |
| `Year`, `Month`, `Day` | `Date[@event="publication"]`, by lexical precision |
| `Writer` | contributors with role `writer` or `script-writer`. The distinction is lost: a projection back into KOMA yields `writer` |
| `Penciller`, `Inker`, `Colorist`, `Letterer`, `CoverArtist`, `Editor`, `Translator` | contributors with the matching role |
| `Publisher`, `Imprint` | `Publication/Publisher`, `Publication/Imprint` |
| `Genre` | `Subject[@type="genre"]`, comma-separated |
| `LanguageISO` | first `Language[@role="content"]` |
| `Manga` | `YesAndRightToLeft` when `direction="rtl"`, otherwise `No` |
| `BlackAndWhite` | `Yes` when `color-mode="monochrome"`, `No` when `color` or `mixed`, omitted when `unknown`. `color` and `mixed` are indistinguishable after projection |
| `AgeRating` | first `Rating` whose `@scheme` is `comicinfo-agerating`; that scheme name exists so the projection can recognize its own output |
| `PageCount` | number of spine entries |
| `Pages/Page/@Type` | mapped from `Item/@roles`: `front-cover`→`FrontCover`, `inner-cover`→`InnerCover`, `back-cover`→`BackCover`, `advertisement`→`Advertisement`, `editorial`→`Editorial`, `letters`→`Letters`, `preview`→`Preview`, `story`→`Story`, others→`Other` |
| `Pages/Page/@DoublePage` | `true` when `page-span="2"` |
| `Pages/Page/@ImageWidth`, `@ImageHeight` | `Item/@width`, `Item/@height` |
| `Pages/Page/@Image` | the 0-based index of the item in the spine. It is not the page file name: see §8.1.1 |
| `Web` | `Link[@rel="other"]` whose target is a record for this publication |

ComicInfo page types with no core role of their own project as follows on the way in: `Roundup` becomes `recap`, `Deleted` becomes `other`. On the way out, every role not named in the table above becomes `Other`, so `recap`, `title-page`, `table-of-contents`, `interlude`, `illustration`, `credits`, `bonus` and `blank` do not survive a round trip.

Not projected: entities, regions, accessibility metadata, provenance, rights, per-page checksums, private-use tokens, extensions.

This projection is lossy in both directions and is not a storage format. A tool MUST NOT reconstruct a KOMA publication from the ComicInfo projection when the core documents are present.

## Annex B — Change log (informative)

### 0.9, fifth draft (this document)

- §10.4: the **pseudocode** now expresses the spine-order invariant. The fourth draft added the invariant as a paragraph and changed the reference implementation, but left the normative pseudocode back-filling exactly as before, so the section prescribed two different behaviours for the same case. Found by external review; the paragraph, the pseudocode, the implementation and the fixtures now agree.
- §5.0: the publication trigger that governs when a `0.x` number must move is stated here, normatively, instead of only in `CONTRIBUTING.md` and in this informative annex, which referred to "§5.0" for a rule §5.0 did not contain. The conformance corpus is excepted from it.

### 0.9, fourth draft

Findings from the first external review, in the reviewer's numbering.

- §10.4: **spine-order invariant** added. A flowing page no longer back-fills the leading half of a spread whose trailing half is taken, which used to place a later spine entry on the side read first (A1). This changes rendered pagination and is the only behavioural change in this draft.
- §4.3: `Decimal01` requires its leading digit (C1); `Path` forbids `%`, `?` and `#` (G4, A4); `Date` lexical space pinned (N8); duplicate `TokenList` tokens and non-empty `Normalized` values named as layer-3 checks (G2); `Color` case named as a warning (G9).
- §4.5: private-use tokens shortened to fit inside `Token` (C2); `Resolution/@unit` and `PhysicalFormat/@unit` added to the closed list (C3); three `Provenance` vocabularies and `AccessModeSufficient` added to the fallback table (C4).
- Line 13: `REQUIRED` and `RECOMMENDED` declared, since both were already used normatively (C10). Lowercase `must` in §15.1 and `may` in §5.1 raised (C9, N9).
- §5.2: the essential-extension exception to safe ignorability stated rather than left implicit (A5).
- §7.8, §7.13, §7.14: child order stated, since the schemas enforce it (A3). §7.14, §7.16, §7.17: those sections may not be empty (N5).
- §9.2: what an absent `PageTarget/@spread-position` means, and that it does not share a value space with `ItemRef/@spread-position` (A6).
- §15, §17: five errors and one warning added; §17 now names what the schemas genuinely cannot carry, several former entries having been fixed in the schemas themselves (G2, G6, G7, G8).
- Annex A: `Web` and `Page/@Image` rows added, the `AgeRating` scheme made self-recognizing, the `BlackAndWhite` projection completed, and the roles that do not survive a round trip listed (Annex A findings).
- Editorial: §10.6's phantom `p4` (N1), `page-span` type (N2), `Certification` attributes (N3), `Manifest/@metadata` requiredness (N4), `PositiveInteger` naming (N7), `@decorative` and `@essential` listed as data types rather than vocabularies (N6).

### 0.9, third draft

- §8.1.1: page naming recommendation written. §15 already warned about "non-recommended file naming" without the specification defining any recommendation; the warning now has a referent, and the 0-based ComicInfo index skew is documented.
- §15.1: conformance corpus defined and shipped, with the pairing fixtures of §10.4.
- §2.1: the sniffing offsets were wrong. The entry name `mimetype` occupies offsets 30–37, so the media type starts at 38, not at 30. Caught by building real packages; corrected to 38–61.

- Format renamed from GRNO to **KOMA**. The previous name expanded to "graphic novel", which is one publishing category among the several the format carries, and contradicted the scope stated in the opening paragraph. KOMA names the panel instead, which every form shares.
- Consequences: extension `.koma`, media type `application/vnd.koma+zip`, internal literals `application/vnd.koma.*+xml`, namespaces `urn:koma:*`, package directory `koma/`, schema filenames `koma-*-0.9.rnc`.
- The container media type is still exactly 24 bytes, so the §2.1 byte layout is unchanged by the rename.

### 0.9, second draft

- §7.17 `Provenance` fully defined: `Source`, `Digitization`, `Note`, with a note on personal data.
- §4.6 and §12: four explicit extension points — the roots of `metadata.xml`, `manifest.xml` and `nav.xml`, plus `Item`. `container.xml` has none. Item-level essential extensions scoped to their page.
- §9: `nav.xml` root element, section order, and the `Entry`, `PageTarget`, `Landmark`, `RegionSequence` and `Region` element definitions that were previously missing.
- §8: full manifest example; `Item` child order fixed; `ItemRef/@item` shown.
- §7.5: the collection name becomes a `Name` element, multilingual, instead of unspecified text.
- §7.11: `direction` is explicitly required, `spread` optional with default `auto`.
- §7.13: accessibility tokens respelled in kebab-case to satisfy the `Token` type, with the schema.org export mapping stated.
- §7.2, §7.3, §7.4: attribute requiredness stated rather than implied.
- §17: schemas written and their limits enumerated; the four `.rnc` files ship with this document.
- §15: errors added for the newly expressible constraints.

The serialized version stays `0.9` because no implementation and no published file exists yet. Once a `0.9` file exists outside this repository, any further incompatible change requires a new number under §5.0.

### 0.9, first draft

- Serialized version lowered from `1.0` to `0.9`; §5.0 defines major version 0 and its exit criteria toward `1.0`.
- Media type changed to the vendor-tree name `application/vnd.koma+zip`; `mimetype` is now 24 bytes, at offsets 38–61.
- Internal document media types renamed to `application/vnd.koma.*+xml` and declared package-internal literals, not registration candidates.
- §18 rewritten around the vendor-tree procedure; the dual-spelling contingency of the previous draft is removed.
- "Release Candidate" labelling dropped in favour of the serialized version.

### Earlier drafts

- Forward-compatible processing mode, minor-version constraints, open vocabularies with private-use tokens and a fallback table (§4.5, §5).
- Data type definitions and document language rule (§4.3, §4.4).
- `Descriptions`, `Publication`, `Subjects`, `Entities`, `Content`, `Accessibility`, `Ratings`, `Links` and `Rights` defined; section order made normative; publication and release identity defined (§7).
- EXIF handling clarified for readers; colour management specified (§8.2, §8.3).
- Optional region-based guided reading (§9.4).
- Normative rendering model with a deterministic spread pairing algorithm (§10).
- Essential extension mechanism defined rather than deferred (§12.1).
- Explicit resource limits and no-scripting statement (§13.1).
- Canonical serialization and reproducible packaging defined (§14).
- Schemas referenced as normative artifacts (§17).
- Lowercase BCP 14 keywords removed throughout.
