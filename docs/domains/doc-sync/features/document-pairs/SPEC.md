# Document Pairs

A declared pair of documents compared by shape: the sequence of blocks each is built from, the
heading levels, and the row counts of the lists and the tables.

**Source:** `src/beadloom/doc_sync/document_pairs.py`

---

## Specification

### Purpose

This repository ships `README.md` and `README.ru.md`, and until BDL-069 nothing held them against
each other. On 2026-09-10 the Russian file carried a paragraph — "there is one honest answer here:
I did not check this" — that stood alone in Russian and was folded into its neighbour in English,
plus an opening sentence the English side did not have at all. The divergence lived between
commits `31f8c9cb` and `97fafca5` and was found by a person reading the two files side by side.

The only number that differed between the two files was a line count, 362 against 360. Nothing
reads that number, and nothing could: a translator wrapping two sentences differently moves it by
the same amount as a missing paragraph does.

### Why the comparison is by shape and never by text

The files are in two languages. A text comparison over a translation reports every line and is
therefore switched off, and a check somebody switches off is the defect class BDL-069 is about.

What survives translation is the **sequence of blocks** a document is built from, with the heading
levels and the row counts of the lists and the tables. A paragraph that exists in one language and
not in the other changes that sequence and is reported. A paragraph the translator wrapped over
three lines instead of two does not.

### The five block kinds

| Kind | What ends it | What is compared |
|------|--------------|------------------|
| `heading` | itself — a heading is one block | its level, as part of the alignment |
| `paragraph` | a blank line or a line of another kind | its presence and its position |
| `code` | the closing fence, or the end of the file | its presence; the body is opaque |
| `list` | a blank line or a line of another kind | its presence and its item count |
| `table` | a blank line or a line that is not a table row | its presence and its data-row count |

A fenced block is opaque on purpose: a `#` inside a shell transcript is a comment and not a
heading, and this repository's own READMEs carry several.

### What it does not compare, and why

- **The line count of a paragraph or of a code block.** Wrapping is a property of the text, and a
  translated sample of a command's output can legitimately differ in length.
- **The prose itself,** in any form.
- **A blockquote and a thematic break,** which read as `paragraph` blocks. Both are still compared
  for presence and position; what is lost is a paragraph rewritten as a quote in one language only.

### The table reading is not this feature's

`doc_sync/tables.py` already answers what a table row is and where one table ends, and two answers
to that question is how one section holding two tables was read as one, twice (BDL-UX #213, #244).
This feature is a caller of that component, not a fifth reader of markdown.

### What a finding can and cannot name

The alignment is `difflib.SequenceMatcher` over block signatures. It names the position at which
the two sequences **diverge**, and the heading that position stands under.

It cannot name *which* of several indistinguishable paragraphs went missing — they have the same
shape, which is the whole reason the comparison works across two languages. The heading is what
tells a reader where to look, and claiming a specific paragraph would be a precision the
comparison does not have.

### The three checks

| Check | Fires when |
|-------|------------|
| `unpaired-block` | one file has a block the other has nothing facing |
| `block-kind` | two blocks face each other and are of different kinds, or two headings sit at different levels |
| `row-count` | two aligned lists or tables carry different numbers of rows |

### Opting in

The pair is declared in `.beadloom/config.yml`:

```yaml
document_pairs:
  - source: README.ru.md
    follower: README.md
```

`source` is the document of record and `follower` is the one that follows it. A project that
declares no `document_pairs:` block is not judged, exactly as with `issue_log:`. Nothing here
guesses a filename: an adopter's translated README is their business, and a check that assumed
`README.<lang>.md` would turn somebody's green tree red on the upgrade that ships it.

A half-written entry — one that names a `source` and no `follower`, or a path that resolves
outside the project root — is refused and logged rather than completed by a guess.

### The population it reports

Every comparison carries the block count of each file and the number of block pairs it aligned,
and a file it could not read is named as unreadable rather than counted as agreeing. A pair over
a missing file compares nothing and says so.

### Surfaces

| Surface | Behaviour |
|---------|-----------|
| `check_document_pairs(project_root)` | every declared pair, the blocks compared, the findings, and the paths it could not read |
| `compare_documents(source, follower)` | two block sequences aligned, for a caller that already read them |
| `read_blocks(text)` | one document as its sequence of blocks |
