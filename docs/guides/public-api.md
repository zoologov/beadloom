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
   Added since 9.0.0 (MINOR, BDL-080 S3c): the value `fsd` of `init --preset`, beside
   `monolith`, `microservices` and `monorepo`.
2. **The keys of `.beadloom/config.yml`.** Every key a command reads, and the values each key
   accepts. A key is documented in the reference of the node whose code reads it: `tests:` in the
   [test-mapping SPEC](../domains/context-oracle/features/test-mapping/SPEC.md), `site:` in the
   [site-generation SPEC](../domains/application/features/site-generation/SPEC.md).
   Keys added since 9.0.0 (MINOR, BDL-080 S4d): `site.logo`, the path of the project's SVG or
   PNG logo relative to its root, shown in the portal's nav; `site.powered_by`, `true` or
   `false`, the "Powered by Beadloom" footer; and `site.repo_icon`, the icon beside the
   header's repository link. `site.repo_icon` takes a value vocabulary: `github`, `gitlab`,
   `bitbucket`, `codeberg`, `gitea`, `azuredevops`, `git`. Without it the icon is read from the
   host of `site.repo_url`, which gives `azuredevops` for an Azure DevOps host as it has since
   8.0.0; BDL-080 S4e let `site.repo_icon` name it for a self-hosted server. `site.logo` is the
   portal's favicon too (BDL-080 S4e); without it, or when the file is Beadloom's own square
   icon byte for byte, the favicon is Beadloom's (the owner accepted that rule on 2026-10-10,
   `beadloom-e1xo`): the theme-adaptive SVG and a PNG per colour scheme under `public/brand/`.
   Key added since 9.0.0 (MINOR, BDL-080 S3a): `imports.aliases`, a mapping of an import alias
   to a folder or file relative to the project root (`.` for the root), read by the reindex
   ([reindex SPEC](../domains/application/features/reindex/SPEC.md#import-aliases)) for the
   import resolver, whose
   [SPEC](../domains/graph/features/import-resolver/SPEC.md#non-relative-jsts-specifiers) says
   how an alias is matched.
   An unknown key under `imports:`, an alias that is a pattern or a path, and a value that names
   nothing in the project are refused by `config-check` and the Gate, with exit code 1; no
   project declared the block before it existed, so no accepted configuration is refused.
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
   Key added since 9.0.0 (MINOR, BDL-080 S4c): the top-level `source_ref`, the revision the
   source links name, present when the file carries source links. It is
   `{commit, linked, pushed}`: `commit` is the full hash the portal was built from; `pushed` is
   `true` or `false`, and `false` only when git says no branch of `origin` holds the commit;
   `linked` is the revision every source link names, either the same hash as `commit` (a pushed
   commit, or an unpublished one no branch stands in for) or the name of a branch on `origin`
   (the branch's upstream when it is on `origin`, `origin`'s branch of the same name, or
   `origin`'s default branch). Both are judged by `origin`'s branches only, even when
   `site.repo_url` names a repository on another forge (a decision of BDL-080 that may be
   revisited).
   Keys added since 9.0.0 (MINOR, BDL-080 S4a): the top-level `lint`, lint's reach over the whole
   project, `{errors, warnings, nodes_with_findings, nodeless}`, where each entry of `nodeless`
   is `{rule, severity, message, file, line}` and `severity` takes the vocabulary `error`,
   `warn`; it is omitted when lint did not run. And a node's `debt.inside`, the debt of the
   nodes inside a box without the box's own, `{nodes, score, by_reason}`, where `by_reason`
   is keyed by the debt report's reasons; it is present on a node another node is `part_of`.
   `dashboard.data.json` is not this file and is not on this list: the keys BDL-080 added to it,
   `lint.nodes_with_findings`, `lint.nodeless` and the top-level `pages`, are described in
   [`dashboard-data.md`](../services/vitepress-site/dashboard-data.md) and carry no promise.
6. **The files generated for an adopter**: what `init`, `docs site`, `docs generate`,
   `setup-agentic-flow`, `setup-rules`, `setup-mcp` and `install-hooks` write into a project,
   their paths and what they mean to the project that receives them.
   Added since 9.0.0 (MINOR, BDL-080 S3): for a Feature-Sliced frontend, `init` writes nine rules
   into `.beadloom/_graph/rules.yml`, two of them of rule types new in this release,
   `slice_public_api: {tags}` and `slice_shape: {tags, segments}` (the
   [rule-engine SPEC](../domains/graph/features/rule-engine/SPEC.md) is their reference); a
   `lint:fsd` script in `package.json`; and, for any project whose `babel.config.*`,
   `.babelrc` or `vite.config.*` declares aliases, the `imports.aliases` block of
   `.beadloom/config.yml`.

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
