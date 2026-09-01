# CLI Commands (component)

The Click command groups the CLI service is assembled from.

**Source:** `src/beadloom/services/commands/`

**Dependencies:** `click`, `rich`, the `application` layer, and — through
`_root` — nothing above it.

---

## Overview

`services/cli.py` used to be one module holding every command. BDL-059 S4 split
it by responsibility: each module here owns one nameable group of commands and
registers them onto the shared `main` Click group defined in `_root.py`.
`beadloom.services.cli` imports the modules to wire them, so
`from beadloom.services.cli import main` still resolves to the same object it
always did.

The node's `source` is the **directory**, not a file. A component whose source
is a package `__init__.py` records that file as its whole surface, and every
symbol reader then sees an empty façade (BDL-UX #157). Pointing at the directory
keeps all fourteen modules inside the node for `module-coverage` and for the
symbol counts.

## Presentation only

These modules parse arguments, call one application or domain entry point, and
render. No command holds a query or a decision: `status` renders what
`application.status.gather_status` read, `guard` renders what
`application.guards.invocation.run_invocation` decided, `review-brief` renders
what `application.review_brief` assembled. A command that starts computing an
answer belongs in the layer below, and `architecture-layers` (severity `error`)
is what holds that line.

## The modules

| Module | Commands |
|---|---|
| `_root.py` | the shared `main` group and the missing-parser warning helper — no command of its own. The summary `beadloom --help` prints is `help=_HELP`, derived from the package docstring rather than written as the group's own docstring: it was a third hand-written copy of the product description and shipped the 1.x sentence through both 3.0 patch releases (BDL-UX #211) |
| `query.py` | `ctx`, `graph`, `why`, `search`, `prime` |
| `index_ops.py` | `reindex`, `doctor`, `diff`, `link` |
| `status.py` | `status` |
| `docsync.py` | `sync-check`, `sync-update`, `install-hooks`, `active-sync` |
| `federation.py` | `export`, `federate`, `lint`, `ci` |
| `docs.py` | `docs generate`, `docs polish`, `docs site`, `docs audit`, `docs quality`, `docs spaces` |
| `setup.py` | `setup-mcp`, `setup-rules`, `setup-ai-techwriter`, `setup-agentic-flow`, `setup-branch-protection`, `config-check`, `mcp-serve`, `init` |
| `dashboard.py` | `tui`, `ui`, `watch` |
| `snapshot.py` | `snapshot save`, `snapshot list`, `snapshot compare` |
| `guard.py` | `guard` |
| `waves.py` | `waves` |
| `review_brief.py` | `review-brief` |

Every module carries `# beadloom:component=cli-commands`, so a module added here
without one is reported by `module-coverage` rather than joining the graph
silently.

## The one command that ends in a verdict

`init` renders its summary and then runs one more application call before it returns: the
Gate's `lint_step` over the graph it has just written, exiting 1 when the graph fails the
rules on disk (BDL-067, closing BDL-UX #192). The check stays
in the application layer and this module only calls it and renders its findings, so the rule
above holds — but the exit code is a decision this command makes, and all three branches that
write a graph make it: `--yes`, `--bootstrap`, and the default interactive wizard. The wizard
was added in BDL-067 `.6` — the verdict shipped at two call sites because the covering tests
counted the two **bindings** of `bootstrap_project` rather than the branches, and the wizard
shares the `--yes` binding. It is skipped on exactly one path, the wizard's `edit` review
answer, where the graph has just been handed to the user to edit and nothing has re-indexed.

Two shapes of failure are rendered separately. Rules that were evaluated and failed are named
as rules; a `rules.yml` the loader refuses is rendered as the loader's complaint, because the
finding the Gate raises there carries the step's own name (`lint`) in `rule` and the reason in
`why` — printing the name told an adopter with a hand-edited rules file that a rule called
`lint` had failed.

The evaluated-rule report also names **whose** rules failed, from the `rules_generated` count
`bootstrap_project` returns. `bootstrap_project` writes `rules.yml` only when the file is not
already there, so on a re-init, or over rules an earlier Beadloom or a hand edit left behind,
the failing rule is the adopter's own. Only a run that authored the file calls the red a
defect in Beadloom's bootstrap and asks for a report; the other says the file was already
there and asks for nothing. `.6` established that fact and applied it to the unloadable-rules
branch alone, which is how the evaluated-rules branch went on blaming Beadloom for a
hand-written `service-needs-parent` until `.9` — measured by the review of `.8` on a scratch
TypeScript project.

Only the wizard branch prints `WITHDRAWN_COMPLETION_CLAIM` before the report. `interactive_init`
prints `Initialization complete!` and its own `Next steps:` before it returns, so the wizard
has claimed success by the time the verdict runs, while `--bootstrap` takes its verdict first
and never makes the claim. One line withdraws it here rather than moving the check into
`interactive_init`, which would put a services-layer decision in the onboarding domain.

That one line precedes **both** report shapes, so it states only what is true of both: the
check did not pass. Until BDL-067 `.12` it read `it does not pass the rules it is checked
against:` and opened the unloadable-rules report, whose next two lines say the graph was not
checked and that no rule was evaluated — the review of `.11` measured the contradiction on two
different unloadable files, so it was the branch and not one parse error. The colon went with
the claim: it promised the list of failing rules that `_report_rules_the_graph_fails` prints
and this branch does not. A second withdrawal string for the second shape was rejected for the
reason `RULES_CONFIG_ERROR` is shared at all — two strings to keep in step is how they drift.
The assertions that hold this are stated over the line as printed rather than over the
constant, so a second string added later is judged by the same claim.

## Related

- `cli` — the registration shell this component is wired into
  ([docs/services/cli.md](../../cli.md))
- `guard-probes`, `bd-seam` — the other two `services`-layer components
