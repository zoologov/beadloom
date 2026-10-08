# The Public API

<!-- beadloom:watches=cli -->

Beadloom's version number follows [Semantic Versioning](https://semver.org/).
The standard's first rule is that the software declares a public API, because a version number is
a promise about that API and about nothing else. This document is the declaration. The
*Public API* section of [`CONTRIBUTING.md`](../../CONTRIBUTING.md#public-api) holds the same list,
and each release's section of [`CHANGELOG.md`](../../CHANGELOG.md) classifies its changes against
it.

The composition below is the owner's ruling of 2026-10-08. A change to the list is itself a change
to the promise, so it is made by the owner and recorded in the change log of the release that
makes it.

---

## What is public

1. **The commands, their options and their exit codes.** Every `beadloom` command and subcommand,
   every option it accepts, and the exit code it returns for a given input. The reference is
   [`docs/services/cli.md`](../services/cli.md) and `beadloom <command> --help`.
2. **The keys of `.beadloom/config.yml`.** Every key a command reads, and the values each key
   accepts. A key is documented in the reference of the node whose code reads it: `tests:` in the
   [test-mapping SPEC](../domains/context-oracle/features/test-mapping/SPEC.md), `site:` in the
   [site-generation SPEC](../domains/application/features/site-generation/SPEC.md).
3. **The keys and the value vocabularies of the JSON outputs**: `ctx --json`, `status --json`,
   the debt report (`status --debt-report --json`) and `export`, whose artifact is JSON without
   an option. A vocabulary is the set of values a key can take. The activity level is one:
   `hot`, `warm`, `cool`, `quiet`, `dormant`. A script that matches on a value depends on the
   vocabulary as much as on the key that carries it.
4. **The MCP tools** the server lists, with their arguments and the keys of what they return. The
   reference is [`docs/services/mcp.md`](../services/mcp.md).
5. **The portal data file's schema**: the `schema_version` the generator writes and the keys under
   it. The reference is
   [`docs/services/vitepress-site/architecture-data.md`](../services/vitepress-site/architecture-data.md).
6. **The files generated for an adopter**: what `init`, `docs site`, `docs generate`,
   `setup-agentic-flow`, `setup-rules`, `setup-mcp` and `install-hooks` write into a project,
   their paths and what they mean to the project that receives them.

**The promise.** Within one major version, nothing on this list is removed, renamed or changed
in a way that breaks a reader that used it as documented. A release that does any of those is a
new major version, and its change log names the change under *Breaking* before anything else.

## What is not public

**Python import paths are not public API.** The modules, classes and functions under `beadloom.*`
can move, be renamed or be removed in any release, and the version number does not say when. They
are laid out by the architecture graph, which decomposes a module when its responsibility splits,
and a promise about import paths would forbid exactly that. A program that needs Beadloom's data
reads it through one of the public surfaces above: `ctx --json`, `export`, the MCP tools or the
portal data file.

The node documents under `docs/domains/` and `docs/services/` carry a section headed *Public API*.
That section describes a module's interface to the rest of this codebase, and it is not part of the
promise this document makes.

## How a change sets the version

| Change to a public surface | Version part |
|---|---|
| A command, option, key, MCP tool or generated file is removed or renamed | MAJOR |
| A value is removed from a vocabulary, or a value keeps its name and changes its meaning | MAJOR |
| The same input gets a different exit code, including a configuration that was accepted and is now refused | MAJOR |
| A reported value that a `--fail-if` threshold judges moves on a project nobody edited | MAJOR |
| A data file schema the released viewer cannot read | MAJOR |
| A command, option, key, MCP tool or generated file is added | MINOR |
| A value is added to a vocabulary | MINOR |
| A schema version that keeps every key of the previous one | MINOR |
| A fix that changes no public surface | PATCH |

A value added to a vocabulary is minor because a reader is expected to tolerate a value it does
not know, as the portal viewer does with an activity level it has not seen. A value removed is
major because a reader that matched it stops matching, and nothing tells it so.

A threshold verdict is the case that is easiest to miss. `status --debt-report --fail-if score>N`
returns its exit code from a score, so a release that changes how the score is counted changes an
exit code for a project that changed nothing. That is listed under *Breaking* even when no key and
no vocabulary moved.

A change is classified by the highest row it reaches, and the change log states, in one sentence
at the top of the release, which line made the version what it is.

## Why the guide watches the CLI

The marker at the top of this file asks `beadloom sync-check` to warn when the command and option
tree changes. A command or option that changes is a public API change by item 1, so the warning is
the prompt to classify it before the release is named.
