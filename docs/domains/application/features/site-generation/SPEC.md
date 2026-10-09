# Site Generation

The `docs site` VitePress content generator for the application domain.

**Source:** `src/beadloom/application/site/` (the package; `generate_site` is re-exported from its
`__init__`)

---

## Specification

### Purpose

Generate a complete VitePress content tree from the indexed graph. `docs site`
reads the graph read-only and emits the About home page, the interactive
architecture view (a canonical layered-lanes Cytoscape+ELK graph), per-node
pages that open that view on their node, the metrics dashboard (data and page),
the cross-repo landscape map, the published `docs/` section, the nav/sidebar
tree, and a generation-time Mermaid validity guard. Since BDL-076 slice 2 it also writes the
portal's hand-written half: the scaffold the package ships (theme, viewer, `package.json`,
lockfile, VitePress config, browser tests) and the identity the project declares in the
`site:` block of `.beadloom/config.yml`, so a project that is not this repository builds its
portal from `docs site` alone.

### The package

Since BDL-076 K1 (`beadloom-ujzb.2`) the portal is one package, `application/site/`, and this
feature node owns it. The modules lived directly under `application/` before, where their
symbols counted against the `application` domain: A1 took that domain to 183 symbols against a
limit of 180, and the owner chose moving the portal over raising the limit. Measured by K1: the
domain owns 14 symbols after the move, and `site-generation` owns 193 in 20 files. A feature is
not judged by `domain-size-limit`. `repository_link.py` joined the package in BDL-076 A3.

The move changed no behaviour and left no shim, so the old dotted paths
(`beadloom.application.site_dashboard`, `beadloom.application.architecture_view`, …) no longer
import. Module names dropped the `site_` prefix the package now carries:

| Before | Now |
|---|---|
| `site.py` | `generate.py` |
| `site_pages.py` | `node_pages.py` |
| `site_landscape.py` | `landscape_map.py` |
| `site_published.py` | `published_docs.py` |
| `site_nav.py`, `site_about.py`, `site_mermaid_guard.py`, `site_metrics_history.py` | `nav.py`, `about.py`, `mermaid_guard.py`, `metrics_history.py` |
| `site_dashboard/` | `dashboard/` |
| `architecture_view.py`, `architecture_card.py`, `landscape_view.py` | unchanged names |

`generate_site` is re-exported from the package, so `from beadloom.application.site import
generate_site`, the entry the CLI uses, reads as it did before.

### Module cluster

One feature node covers the cooperating modules below (all annotated
`# beadloom:feature=site-generation`, all under `application/site/`):

- **generate.py** — `generate_site(conn, out_dir, *, project_root, federated=None,
  now_ts=None)` is the `docs site` use-case: it reads the indexed graph read-only and writes a
  VitePress content tree under `out_dir` (default `site/`) — an `index.md` **About home page**
  rendered from the project `README.md` via `about.render_about` (link-rebased; falls back to
  the architecture overview body when no `README.md`), a `ru/index.md` RU About page from
  `README.ru.md` (omitted when absent; both About pages get the in-page bilingual cross-link
  `/` ↔ `/ru/` via `cross_link_routes`), an `architecture.md` architecture page — the
  interactive Cytoscape+ELK compound graph primary view (`public/architecture.data.json`,
  delegated to `architecture_view.py`) plus the Mermaid counts/C4/health overview demoted to
  the `architecture-diagram.md` fallback (the body that used to live at `index.md`, BDL-046;
  the Mermaid graph was unreadable so the interactive view is now primary, BDL-060 S4 ext), a
  `docs/index.md` Documentation overview (BDL-046 BEAD-11: a short intro + one `## <Group>`
  heading per top-level docs group — Domains / Services / Guides / General — each followed by a
  single sentence that **names** its members as inline human-labelled TEXT, **no link wall**,
  since the full navigable tree is already the expanded Documentation sidebar), one page per
  node (delegated to `node_pages.py`), the metrics dashboard (`dashboard.md` +
  `dashboard.data.json`, delegated to the `dashboard/` package), the 🌟 landscape map — the
  interactive Cytoscape+ELK primary view (`landscape.md` + `public/landscape.data.json`,
  delegated to `landscape_view.py`) plus the Mermaid fallback (`landscape-diagram.md`,
  delegated to `landscape_map.py`), and `.vitepress/config.generated.mjs` (nav/sidebar). Before
  building the dashboard it backfills structural trend history from `graph_snapshots` and
  records this run's honest metrics point (`metrics_history.append_metrics_point`) so the
  emitted trend series includes "now"; `now_ts` is the injected ISO timestamp of the run
  (deterministic in tests; defaults to the current UTC instant in production). It is the only
  wall-clock read, and it lands in two places: the append-only history store and the
  `generated_at` field of `architecture.data.json` (BDL-076 A1). No dashboard field carries it,
  so a fixed `now_ts` regenerates the tree byte for byte. Since A1 the run also computes each
  node's lint findings (`_lint_findings`, the same `beadloom lint` run the dashboard reports)
  and debt (`_node_debt`, the debt report's scored offenders, read and never re-scored), hands
  both to `architecture_view` as `NodeVerdicts`, links every node to its page through
  `node_pages.node_page_urls` (both landscape views use the same map), and reads the
  repository a node's source links into through `repository_link.repository_of`. Beadloom
  produces, VitePress renders. Output is
  deterministic (sorted, stable frontmatter) and never writes into the source `docs/`. Returns
  a frozen `SiteResult` listing every written path. Reuses `graph/c4.py`
  (`map_to_c4`/`filter_c4_nodes`/`render_c4_mermaid`) for diagrams; reimplements no graph
  logic. Every emitted Markdown page is run through the Mermaid structural guard
  (`mermaid_guard.validate_mermaid`) before writing — a structurally broken diagram raises
  `MermaidValidationError` and fails generation (closing the "build green ≠ renders ok" gap)
  instead of shipping a page that crashes the browser render.

  **Slice 2 (BDL-076 B1, B4, `beadloom-ujzb.11`–`.13`).** The run first reads the identity
  (`site_config.site_config_of`; a refused value raises `SiteConfigError` before any file is
  written) and one `RepositoryLink` for every link: `repository_of(project_root,
  declared_url=identity.repo_url, forges=identity.forges)`, where a declared `site.repo_url`
  wins over the `origin` remote. The node card's `source_url` may come from the remote; the
  project's own text links only to a repository the project DECLARED, so with no `repo_url`
  a link to a repository file becomes its text. Every piece of project text — the README pair
  on the About pages, each node's summary, every published document — goes through
  `project_text.render_project_text` with one `PortalLinks` (`about.portal_links_for`,
  carrying the base and the published files). `ru/index.md` is written, and `README.ru.md`
  routed to `/ru/`, only when `README.ru.md` exists. After the content it writes
  `.vitepress/site.generated.mjs` (`site_config.render_site_module`), copies the project's logo
  when `site.logo` names one (`site_logo.copy_logo`, to `public/logo.svg` or `public/logo.png`),
  writes Beadloom's favicon into `public/brand/` when the portal shows it
  (`favicon.uses_beadloom_favicon`, `favicon.write_beadloom_favicon`, BDL-080 S4e), and then the
  scaffold
  (`scaffold.write_scaffold`, which copies `.beadloom/site/` last); `SiteResult.scaffold` is the
  `ScaffoldReport` of that write.
- **site_config.py** — the portal's identity, the `site:` block (BDL-076 B1, B4 and
  `beadloom-ujzb.20`). `read_site_config(project_root)` returns `(SiteConfig, refusals)` with a
  refused value replaced by its default, and `site_config_of(project_root)` raises
  `SiteConfigError` on any refusal. `SiteConfig(title, description, base, repo_url, forges, logo,
  powered_by, repo_icon)`; defaults: the project directory's name,
  `The architecture of <title>: its graph, its documentation and its health`, `/`, no
  repository, no logo, the footer on, the icon read from the host. The keys are one table,
  `_FIELDS` (`title`, `description`, `base`, `repo_url`, `forges`, and since BDL-080 S4d
  `logo`, `powered_by`, `repo_icon`); an unknown key is refused by name with the keys the block reads. `base` must start
  and end with `/` and hold no GitHub Actions expression opener. `repo_url` must be an `http(s)` address with a host and no credential, query or fragment; it is stored in one
  spelling by `canonical_repo_url` (scheme and host lower-cased, port and path case kept,
  trailing `/` and one `.git` removed). On a host with a known forge it is refused by name in
  two cases (`beadloom-ujzb.23`, n2): when it stops before a repository
  (`forge_routes.stops_before_repository`; the refusal names how the forge writes one, such as
  `/<owner>/<repository>`), and when it runs past the repository into a page of it
  (`forge_routes.runs_past_repository`). On any other host nothing says which segment of the
  path is a route, and nothing is refused.
  The value itself is never repeated in a refusal, because it may hold a credential.
  `powered_by` must be a boolean, and `repo_icon` one of `REPO_ICONS`. `logo` is read twice
  (`site_logo`): its shape where the block is read, and the file against the project root after.
  `render_site_module(config, project_root)` writes `.vitepress/site.generated.mjs` as JSON, with
  `repoIcon` from `repo_icon_of` and, since BDL-080 S4d, `logo` (the copy's address before the
  base, `""` without one) and `poweredBy`; since S4e, `logoMonochrome` (`site_logo.is_monochrome`)
  and `favicons` (`favicon.favicons_of`), both read from the logo file under `project_root`. `unlinked_repository(project_root)` returns the sentence
  `config-check` prints, without blocking, when a declared `site:` block has no `repo_url`, and
  `""` otherwise. The refusals
  reach three readers: `docs site`, `beadloom config-check` and the Gate's `config-check` step
  (rule `site-config`).
- **repository_icon.py** — the icon beside the header's repository link (BDL-080 S4d,
  `beadloom-af99.7`, the owner's ruling of 2026-10-09). `repo_icon_of(repo_url, forges=None,
  declared="")` is `""` without a repository; else the declared `site.repo_icon`; else the kind
  of a forge the project declares for the host; else the host: `github.com` `github`,
  `gitlab.com` and a host whose first label is `gitlab` `gitlab`, `bitbucket.org` `bitbucket`,
  `codeberg.org` `codeberg`, `gitea.com` and a host whose first label is `gitea` `gitea`,
  `dev.azure.com` and `*.visualstudio.com` `azuredevops`; else `git` (`GENERIC_ICON`).
  `REPO_ICONS` is the vocabulary `site.repo_icon` accepts: `github`, `gitlab`, `bitbucket`,
  `codeberg`, `gitea`, `azuredevops` (since BDL-080 S4e), `git`. Before S4d `codeberg.org` drew
  Gitea's mark.
- **site_logo.py** — the project's logo in the nav (BDL-080 S4d). `read_logo(value, where)` keeps
  a non-empty relative path with a `.svg` or `.png` suffix (`LOGO_SUFFIXES`) in posix form and
  refuses anything else by name; `logo_problem(project_root, logo, where)` refuses a path that
  resolves outside the project root or holds no file; `logo_site_path(logo)` is `/logo.svg` or
  `/logo.png` (`""` without a logo); `copy_logo(project_root, logo, out_dir)` copies the file
  byte for byte into `out_dir/public/` and returns the copy, or `None` without a logo.
  `is_monochrome(project_root, logo)` (BDL-080 S4e) is whether the logo is an SVG that holds
  `currentColor`, which the nav then draws in the text's colour; `False` for a PNG and without a
  logo.
- **favicon.py** — the portal's favicon (BDL-080 S4e, `beadloom-af99.9`, the owner's look of
  2026-10-09). `uses_beadloom_favicon(project_root, logo)` is true without a logo and for a logo
  that is Beadloom's icon byte for byte (`site_scaffold/public/brand/beadloom-icon.svg`).
  `favicons_of(project_root, logo)` is then Beadloom's three, `/brand/beadloom-favicon.svg`
  (`image/svg+xml`), `/brand/beadloom-favicon.png` (`image/png`, `sizes` `32x32`) and, since
  `beadloom-e1xo` (the owner's ruling of 2026-10-10), `/brand/beadloom-favicon-dark.png` (the
  same, with `media` `DARK_SCHEME`, `(prefers-color-scheme: dark)`), and otherwise the logo's
  copy alone with its type. `write_beadloom_favicon(out_dir)` copies the three files from the
  package data `beadloom/site_favicon/` into `public/brand/`: not scaffold files, because a PNG
  cannot carry the scaffold's text marker. `LIGHT_GLYPH` (`#3c3c43`) is the colour the first PNG
  carries, the SVG's light scheme, and `DARK_SCHEME_GLYPH` (`#dfdfd6`) the second's, its dark
  scheme; `FAVICON_PNG_SIZE` is 32. The PNGs are generated from the SVG, one per scheme, by
  `tests/support/render_favicon_png.mjs`.
- **forge_routes.py** — the routes a forge serves a path under (BDL-076 `beadloom-ujzb.8`).
  `Forge(kind, tree, blob, raw)` holds three URL templates over `{url}`, `{ref}`, `{path}`;
  `link(route, url, ref, path)` fills one, URL-encoding the revision and the path.
  `KNOWN_FORGES` covers `github`, `gitlab`, `gitea`, `bitbucket` (Bitbucket Cloud) and `azure`;
  `forge_for(web_url, declared)` looks up a host the project declares first, then the public
  hosts (`github.com`, `gitlab.com`, `bitbucket.org`, `codeberg.org`, `gitea.com`,
  `dev.azure.com`, `*.visualstudio.com`). `read_forge(setting)` reads one `site.forges` value: a
  kind, or a mapping with a required `source:` template (used for the page of a path and of a
  file) and an optional `raw:` template (the file itself); `template_problem(template)` refuses
  an unknown placeholder, a conversion or format spec, a template without `{path}`, one that does
  not yield an `http(s)` address, and one carrying a credential.
  `runs_past_repository(web_url, forge)` is true when a route segment of the forge (`tree`,
  `blob`, …) comes after the owner and the repository and something follows it, and, since
  `beadloom-ujzb.23` (n2), when the path runs past where that forge's repository address ends:
  GitHub and Bitbucket Cloud serve a repository at exactly `/<owner>/<repository>`, and so does a
  Gitea on a public host; on a declared Gitea host a Gitea page segment (`src`, `pulls`, …) past
  the second segment that is not the last one; on GitLab a reserved route word (`-`, `tree`,
  `blob`, …) past the second segment; on Azure DevOps anything past `_git/<repository>`.
  `stops_before_repository(web_url, forge)` returns the forge's repository shape when the path
  is shorter than it (fewer than two segments, or an Azure DevOps address with no
  `_git/<repository>`), else `None`; a forge declared by a template has no shape and is never
  refused by it. A GitLab subgroup named like a reserved word past the second segment is
  refused, and a declared Gitea or GitLab host is not held to two segments, since it may serve
  under a path. The routes were written from
  the forms the forges publish, not opened against a live forge; the Azure DevOps `raw` route
  is the least certain.
- **scaffold.py** — the shipped scaffold and the project's overrides (BDL-076 B1,
  `beadloom-ujzb.18`). The scaffold is package data under `beadloom/site_scaffold/`, laid out as
  it sits in a portal. `write_scaffold(out_dir, *, project_root, version)` writes each shipped
  file with a marker line (`beadloom:generated version=<v> sha256=<hash of the rest>`, a comment
  in `.js`/`.mjs`/`.vue`/`.css`/`.svg`, a `"//"` key on the second line of a `.json`): an absent
  file is
  written; a file with an intact marker is rewritten when the shipped body or the version
  differs; a file with no marker, or whose body no longer matches its marker, is never
  overwritten and is reported as a `KeptFile` with its remedy. A file with an intact marker that
  the installed version no longer ships is removed (`retired`). Since BDL-080 S2d a folder those
  removals leave empty is removed with them (`retired_folders`, `_retire_emptied_folders`),
  deepest first: the candidates are the folders a retired file sat in and the folders above them,
  never the portal's root, so a folder the project made is never touched and one that still
  holds anything, a file beadloom did not write included, stays. Without it a slice the scaffold
  renamed outlived the version that wrote it as an empty tree: a portal written by 8.0.0 and
  rewritten after the S2c renames kept six empty leaf folders under `entities/` (measured by
  S2d: `42 retired, 9 empty folders retired`, 0 empty folders left). `.beadloom/site/` (`OVERRIDE_DIR`)
  is copied last and verbatim, and a shipped path it provides is not written at all.
  `shipped_files()` returns each body without the lines that are only a graph annotation
  (`without_annotations`), so a portal never names this repository's nodes; the marker hashes
  the body as written. `marker_line(body, version, note)` and `place_marked(target, expected)` are
  shared with the Pages workflow. `ScaffoldReport` counts `written`, `updated`, `unchanged`,
  `retired`, `retired_folders`, `kept` and `overridden`.
- **pages_workflow.py** — `docs site --pages-workflow` (BDL-076 B2, `beadloom-ujzb.13`, `.20`).
  `write_pages_workflow(project_root, *, out_dir, base, version, branch=None)` writes
  `.github/workflows/beadloom-portal.yml` (`PAGES_WORKFLOW_PATH`) under the scaffold's marker
  rule, and returns a `PagesWorkflowReport(path, outcome, base, node_major, site_dir, branch,
  reason, remediation)`. The workflow installs `beadloom[languages]==<version>` on Python 3.12,
  runs `beadloom reindex` and `beadloom docs site --out <dir>`, sets up the Node major
  `node_major_of` reads from the scaffold's `engines.node` (22 today), runs `npm ci` and
  `npm run docs:build`, uploads `<dir>/.vitepress/dist` and deploys it. It grants nothing at the
  top (`permissions: {}`); `build` reads (`contents: read`, `pages: read`); `deploy` alone has
  `pages: write` and `id-token: write`. The push trigger names the branch `default_branch_of`
  reads from `origin/HEAD` (none when git records none), and the build runs only when the ref is
  a branch and the repository's default branch. A step fails the build when `site.base` differs
  from the path `configure-pages` reports. Every action is pinned by commit SHA with its release
  in a comment. `site_dir_of` refuses an `--out` outside the project; any value holding a GitHub Actions
  expression opener is refused (`PagesWorkflowError`). Since BDL-078 `beadloom-btkd.9` the
  checkout step takes `fetch-depth: 0`: the reindex measures each node's activity on the history
  the clone holds, and a checkout one commit deep shows every file as added. An adopter's
  workflow gets it on the next `--pages-workflow` run while the file is as beadloom wrote it.
- **pages_base.py** — the local base warning (BDL-076 `beadloom-ujzb.13`).
  `project_pages_base(remote)` is `/<repo>/` for a `github.com` project repository and `None`
  for anything else (another host, a `<owner>.github.io` repository, no remote);
  `base_warning(base, remote)` returns the warning `docs site` prints on stderr when `base` is
  `/` and the remote is such a repository. The remote is read only to warn.
- **markdown_links.py** — the one link rule for project text on the portal (BDL-076
  `beadloom-ujzb.11`, `.12`, `.8`, `.21`). `PortalLinks(doc_slugs, page_routes, repository,
  withheld, base, mirrored_files)` says what the portal publishes;
  `rebase_links(markdown, portal, *, source_dir, mirrored_dir, page_dir, front_matter)` resolves
  each link against the file the text came from: a published file goes to its page; a link
  inside the mirrored `docs/` stays as written, or becomes its text when the portal does not
  publish the target; an image the portal publishes is referenced from the page's directory;
  any other repository file goes to the declared repository's `blob` route (an image to its
  `raw` route) at the generated commit, or becomes its text with no repository, commit or known
  forge; a target outside the repository becomes its text; an absolute address, `//host`, an
  anchor and an empty target are left alone. Reference definitions are rebased too, and a
  withdrawn one turns every reference naming it into text. Links are read from markdown-it's
  tokens (`markdown_source.read_markdown`), so a link whose text is code is a link and anything
  in code or raw HTML is not. `raw_html_destination(url, portal, ...)` applies the same rule to
  a raw `href`/`src`, writing a page's address in full under the base.
- **project_text.py** — project text as a page shows it, never as a Vue template (BDL-076
  `beadloom-ujzb.12`, `.21`). `render_project_text(markdown, portal, *, source_dir, mirrored_dir,
  page_dir, opens_page=True)` rebases the links and then changes the text only where Vue would
  read it: a pair of opening braces in rendered text gets an empty HTML comment between the
  two braces; a code span holding such a pair becomes
  `<code v-pre>`; an indented block holding one is wrapped in `<div v-pre>` inside its own list
  item or quote (when the block opens a list item, the wrapper starts one space after the
  marker, and a quote marker written with no space gets one in the inserted lines); a fenced
  block's content and readable front matter are left alone. Since `beadloom-ujzb.23`: an
  autolink, or a bare `http(s)`/`ftp` address VitePress's linkify links, whose linked text
  decodes a brace pair from percent-escapes is written as the link it renders,
  `[address](<address>)`, and its text is then read like any other (M1). A brace VitePress's
  markdown-it-attrs would read as the start of attributes (`markdown_attrs.attribute_braces`)
  gets a backslash before it, which renders as the brace and which the plugin never reads; an
  image's label or a container's info string that ends with attributes
  (`markdown_attrs.ends_with_attributes`) gets an empty HTML comment after it (M2). A project's
  own `{#id}` is therefore shown as written, not applied: a repeated id stops the build, and a
  forge does not apply it either. A fence's info string holds `<`, `"` and a brace pair as
  entities, since VitePress writes it into the page as it is (n1). With `opens_page=True`, front
  matter gray-matter cannot read (`vitepress_markdown.front_matter_is_read`) would fail the
  build at the top of the page, so the text then starts with a blank line and the block is read
  as Markdown (m1). Raw HTML is read as Vue's
  tokenizer reads it (`raw_html.read_markup`): a tag is kept only when it is lowercase README
  HTML (`_KEPT`) balanced inside the element markdown-it writes, and anything else becomes text;
  Vue-only attributes (`@x`, `#x`, `.x`, `[x]`) are dropped and a directive the DOM can hold gets
  `v-pre`; `<script>`, `<style>`, `<template>`, `<iframe>`, `<textarea>` and Vue components
  (`<Badge>`) become text. An `<a>` with nowhere to go keeps its content and an `<img>` becomes
  its alt text. The pass repeats until it changes nothing. `opens_page=False` (node summaries)
  reads a leading `---` block as Markdown rather than front matter.
- **vitepress_markdown.py** — markdown-it-py configured as VitePress 1.6.4 configures
  markdown-it (BDL-076 `beadloom-ujzb.21`): the `js-default` preset with HTML on, the
  `@mdit-vue/plugin-component` HTML rules and `markdown-it-container` under VitePress's names
  (`tip`, `info`, `warning`, `danger`, `details`, `v-pre`, `raw`, `code-group`), ported line for
  line. `vitepress_markdown()` returns the parser; `front_matter_length(text, *,
  closed_only=False)` follows gray-matter's rule for where front matter ends, and
  `front_matter_is_read(text)` whether gray-matter, as VitePress runs it, parses the block
  without an error (`beadloom-ujzb.23`, m1). PyYAML stands in for js-yaml 3 with js-yaml's
  reading of keys: a key is the string JavaScript makes of it, so a key written twice in that
  sense is refused, and a list or a mapping may be a key. Only YAML is read (no language, or
  `yaml`, on the opening line). Where the two parsers part, the answer is no: a tab PyYAML
  refuses, and two keys that start like numbers. A wrong no costs a block shown as Markdown,
  never a failed build. `linkify`, emoji, anchors, alerts, the table of contents, `<<<`
  snippets and `@include` are not followed, each argued in the module docstring; a bare
  address whose linked text decodes a brace pair is handled in `project_text`, and where
  markdown-it-attrs reads a brace is mirrored in `markdown_attrs`. Checked against VitePress's
  own parser over 142 Markdown files of this repository and R2's cases: no difference in block
  tokens beyond anchors and table-cell line maps. The dependency is pinned
  `markdown-it-py>=4.0,<5`.
- **markdown_attrs.py** — where VitePress 1.6.4's markdown-it-attrs 4.x would read a brace as
  the start of attributes (BDL-076 `beadloom-ujzb.23`, M2). The portal sets no
  `markdown.attrs`, so the plugin runs with its defaults: `{` and `}` delimit attributes and
  every attribute name is allowed, so Vue compiles a `:x`, `@x`, `v-x` or `#x` it moves onto an
  element. The mirrored patterns: the end of a block or a list item, a line of its own after a
  soft break, right after a closing inline element, an image or a code span, a paragraph of its
  own right after a table or a list, a thematic break written as `*** {...}`, an image's label
  and a container's info string. `attribute_braces(text, *, opens, closes, alone)` returns the
  indices of the braces in one run of an inline token's text the plugin could read as a left
  delimiter (`opens`/`closes`: the run starts or ends its inline token; `alone`: the inline is a
  paragraph right after a table or a list). A run here may be several markdown-it tokens, so the
  reading is a superset of the plugin's: a brace named that the plugin would not read gains a
  backslash that renders as nothing. `ends_with_attributes(text)` is the plugin's end test on a
  label read as written, escapes included.
- **markdown_positions.py** — wraps that parser's rules so every token carries its source
  offsets (`located_markdown()`); `normalise(text)` normalises line endings and NUL the way
  markdown-it does before parsing. Since `beadloom-ujzb.23` it also records an autolink's
  rendered text (the address with its percent-escapes decoded) and its destination (`mailto:`
  added for an e-mail address), a fence's info-string span, and where a container's info line
  ends.
- **markdown_source.py** — `read_markdown(text, *, front_matter=True)` returns a
  `MarkdownSource` with `parts` (`Element`, `RawHtml`, `Text`, `CodeSpan`, `CodeBlock`,
  `Autolink`, `RawLabel`, in page order), `links` (`Link`), `definitions` (`Definition`) and
  `code` (`CodeRegion`); `Edit` and `apply_edits(source, edits)` change the source at exact
  offsets. A `Text` carries `opens`, `closes` and `alone`, which say where it sits in its inline
  token for `markdown_attrs`. A `CodeBlock` carries `lead` (what goes between an inserted line's
  position and its text) and, for a fence, `info` (the info string's source span). `Autolink(start,
  end, label, destination)` is an autolink written `<address>`; `RawLabel(end, label)` is text
  markdown-it-attrs reads as written, an image's label or a container's info string.
- **raw_html.py** — `read_markup(html)` returns the `Markup` (tags, comments and their
  `Attribute`s) of a raw HTML fragment as Vue's tokenizer reads it, marking `unreadable` what Vue
  would report as an error.
- **architecture_view.py** — the interactive **architecture** data model
  (`architecture.data.json`): each node carries its `layer`, its `layer_rank`
  (the partition index for the canonical layered-lanes layout — the index of the
  node's layer in the declared order, inherited from the nearest layered
  container when the node declares none), symbol count, doc-status, served
  `.html` doc links (gated by the published-slug set so a link never 404s), and
  the `beadloom why` dependency lists; each `depends_on` edge carries a
  `violation` flag (true when any of the project's layer rules finds against that edge).
  Since BDL-080 S1b it also writes every layer rule the project declares (`layer_rules`) and,
  per node, the rule that places it (`layer_rule`, `layer_rule_rank`), read through
  `layer_rules_view.py`. The original keys `layers`, `layer_order`, `layer` and `layer_rank`
  still describe one rule, the first `layers` rule by name, and since S1f they read that rule
  inside its `scope:`. Honest degradation throughout.

  **Which layers exist is read, not written down here (BDL-070 A5).** The view
  held a table of four `layer-*` tags and a table of four ranks and climbed
  `part_of` in a loop of its own — one of the three disagreeing answers to "what
  layer is this node in" that BDL-070 exists to remove. It now reads the layer
  order from the indexed `rules` table (the same graph every other read in the
  module goes through, so generating the site needs no second path to
  `rules.yml`) and resolves membership through `graph.rules.layers`, which is
  what the rule engine decides on. A graph whose index carries no layer rule
  gets no lanes rather than every node in lane 0.

  **That is the one adopter-visible change of rendered output in Release A**, and
  it is stated here because nothing else would show it: a project that carries
  `layer-*` tags and declares no layer rule rendered four lanes before and
  renders none now. This repository declares the rule, so nothing moves here —
  which is exactly why the case would go unnoticed. The view cannot tell which
  layering such a project meant, so it logs the case at INFO with the number of
  tagged nodes instead of drawing a stratification nobody declared.

  The `layer` field stays the short token — the declared tag with its
  conventional `layer-` prefix removed — and a tag that does not carry the prefix
  is used verbatim. Since BDL-076 A2 the viewer holds no table of those tokens:
  its `site-layers` slice (`entities/layers/model/layers.js`) builds the layers
  from the `layer_rank` values that occur, names each one by the `layer` of a
  node that declares it, and colours it by its position in the order, so an
  adopter whose layers are called differently gets its own names. `layer` reads
  the node's OWN tag while `layer_rank` inherits: the card states what the node
  declares, and the layout needs a lane for a feature that declares nothing.

  **The edge `violation` flag is the rule engine's verdict, asked of the rule
  (BDL-070 B4).** It was this module's own predicate — `dst_rank <= src_rank`,
  true for every edge pointing up AND every edge staying inside one layer — and
  it was the last of the three disagreeing answers this epic set out to remove.
  Measured on this repository on 2026-09-13, over a warm full rebuild of the
  index: the view drew 130 edges red that `beadloom lint` finds nothing against,
  116 of them dependencies between two parts of one domain and 14 crossings
  `rules.yml` excuses by name. The view now calls
  `graph.rules.layer_edges.flagged_layer_edges`, so an edge is red here exactly
  when the Gate reports it — direction, layer skip, the same-layer predicate
  RFC Q1 decided and the project's `exempt:` entries, none of them stated twice.

  **The rendered artifact moves for those 130 edges**, from `"violation": true`
  to `"violation": false`, which is what B4 changes about the picture. The flag
  stays OMITTED for an edge with an end in no declared layer: the rule does not
  judge such an edge, and drawing it as healthy would be the same overclaim in
  the other direction.

  **Since BDL-080 S1b the verdict is the union over every rule.** The view asks
  `flagged_layer_edges` of each `layers` rule over `depends_on` and marks an edge
  `violation: true` when any of them finds against it. The key is written when the
  first rule by name ranks both ends, as before, or when any `depends_on` rule places
  a layer at both ends (`LayerRulesView.judges`). Measured on this repository by S1b:
  the edges and their `violation` keys were byte-identical to the build before it,
  because the first rule already ranks both ends of every edge the second one judges: the
  site's slices inherit `layer-service` from `vitepress-site`.

  The rule's `exempt:` entries reach the view through the indexed rule, so
  `reindex` carries them into `rules.rule_json`. An index written by an earlier
  release carries none, and a project that excuses crossings and regenerates its
  site without reindexing sees those crossings drawn red until it does.

  A layer rule declared over an edge kind other than `depends_on` flags nothing
  here. This picture renders the verdict on dependency arrows, so such a rule is
  reported by `beadloom lint` and drawn by nothing — a gap in what the picture
  shows rather than a disagreement about what is true.

  It also carries **declared runtime coupling** (`uses` edges) — a subprocess
  call or a file-format contract — as `uses` / `used_by`, kept SEPARATE from the
  import lists and drawn dotted, never flagged as a violation: crossing a
  process boundary to call a published interface is not a layering break the way
  an import is, and folding it into `depends_on` would assert a binding that
  does not exist. The view previously filtered these edges out entirely, so
  authored architectural intent already present in the graph — every
  `cli uses <domain>` among them — was silently absent from the picture,
  and a node coupled only that way (`ai-techwriter`, which shells out to the CLI
  and hands the dashboard a run-record file) read as an island.

  **Honest degradation**: a node with no doc gets EMPTY `doc_links` (no
  fabricated link, and a link is emitted only for a slug that was published, so
  it never 404s); no declared layer tag gives an empty `layer`; `lint_clean` and
  `findings` are OMITTED when lint was not computed rather than reported clean.
  `serialize_architecture_view(data)` is the byte-stable JSON (`sort_keys`), and
  `render_architecture_view_md(data)` renders `architecture.md` — title, intro,
  the `<ClientOnly><ArchitectureMap></ClientOnly>` mount, a static count summary
  for a reader without JavaScript and a link to the `architecture-diagram`
  Mermaid fallback. Since A1 its intro names the declared layers from the data
  file (`The lanes are the declared layers, top to bottom: …`, or that the
  project declares none) instead of a fixed list. Since A3 it also names the four
  drawn edge kinds, the legend, the card, the neighbourhood's depth and direction,
  **Impact**, the filters and the URL state. The file is written to
  `site/public/architecture.data.json` for the runtime
  `withBase("/architecture.data.json")` fetch. The rendering lives in the
  VitePress theme: `ArchitectureMap.vue` is a thin page over the `graph-viewer`
  widget and the `node-card` widget, described in [the site's
  page](../../../../services/vitepress-site.md).
- **layer_rules_view.py** — every layer rule the project declares, as the architecture view
  draws it (BDL-080 S1b, RFC D2). The view drew one stratification, the first `layers` rule by
  name, so a repository with a backend and a frontend drew its frontend grey while
  `beadloom lint` judged it. `declared_layer_rules(conn)` reads every `layers` rule from the
  indexed `rules` table, ordered by name, with its `exempt:` entries, its `scope` and its
  `title`. A row that is not readable JSON, or declares no layer, is left out and logged, so one
  unreadable rule does not take the others' strata with it. `layer_rules_view(rules, parents,
  tags)` builds a `LayerRulesView` in which each rule reads only the tags inside its scope
  (`graph.rules.layers.within_scope`, the narrowing the linter applies). The view answers three
  questions, each from the rule engine's arithmetic:
  - **which rule places a node** (`placement`) — the rule whose tag the node carries itself
    (distance 0), else the rule of its nearest tagged `part_of` ancestor (distance = the
    generation). At one distance the first rule by name wins. A scoped rule places nothing
    outside its subtree.
  - **which container a rule stratifies** (`declared`) — the declared `scope:`, else the lowest
    container that is a strict `part_of` ancestor of every node the rule places a layer on (a
    container holds its parts and is not its own), else `""` when the rule places no node or no
    single container holds them all.
  - **which edges are found against** (`flagged`) — the union of `flagged_layer_edges` over
    every rule whose `edge_kind` is `depends_on` (`FLAGGED_EDGE_KIND`). A rule over another edge
    kind is reported by `beadloom lint` and drawn by nothing here.
- **architecture_card.py** — the node card of `architecture.data.json` (BDL-076
  A1): what one node shows beyond its place in the graph. `card_sources(conn, *,
  tags, verdicts)` reads the per-build inputs once — the test placements, the
  owner of each test file the graph holds (`test_owners`), the `NodeVerdicts` the
  site run computed and the `RepositoryLink` — and `card_fields(...)` projects one
  node's `source`, `source_url`, `lifecycle`, `tags`, `docs`, `tests`,
  `public_symbols` and `activity`, plus `findings` and `debt` when those were
  computed. `architecture_view` merges the result into each node. `activity` is
  narrowed to `CARD_ACTIVITY_KEYS` (`commits_30d`, `lines_30d`, `level`) by `card_activity`: the
  reindex also records the names of a node's most frequent committers, and the data
  file is published, so a key reaches it only by being listed there (BDL-076 R1
  finding M2). The fields and their shapes are listed under the data file below.
- **repository_link.py** — where a node's source can be read on the web (BDL-076 A3, reworked
  by R1 finding M1, the re-review's m1–m3 and `beadloom-ujzb.8`).
  `repository_of(project_root, *, declared_url="", forges=None)` returns a
  `RepositoryLink(url, ref, forges)`: the declared `site.repo_url` wins, and the project's own
  `origin` remote (`origin_remote(project_root)`) is read only when nothing is declared; the
  revision is the current commit, empty unless `project_root` is the top of its own git
  repository. `web_url_of_remote(remote)` turns HTTP(S), `ssh://` and scp-like remotes into a
  web address: credentials, user names, the SSH port and a trailing `.git` are dropped, and
  Azure DevOps' `v3/<org>/<project>/<repo>` SSH form becomes its `_git` web address. A remote a
  browser cannot open (a path on disk, `file://`), an Azure SSH remote in its legacy form, an
  IPv6 host and a port that is not a number give `""`, never an error, because the link is an
  extra of the site. `RepositoryLink.source_url(source)` (the `tree` route), `file_url(path)`
  (`blob`) and `raw_url(path)` (`raw`) build the finished link at the recorded commit by the
  forge `forge_routes.forge_for` finds for the host: a host the project declares in
  `site.forges`, else a public forge's own host. Any other host gets no link, because a guessed
  route is a 404 that looks like a link. The remote reaches the data file only as each node's
  `source_url`: no screen reads the address, and a remote can hold a credential where no parser
  expects it. Since BDL-080 S4c (`beadloom-e1xo`) the revision is `source_ref.source_ref_of`'s
  `linked`, and `RepositoryLink.source` carries the `SourceRef`; a branch is linked by the
  forge's branch routes (`forge_routes.on_branch`).
- **source_ref.py** — which revision the source links name (BDL-080 S4c, `beadloom-e1xo`,
  BDL-UX #307). `source_ref_of(project_root, commit)` returns `SourceRef(commit, linked,
  pushed)`: `pushed` and `linked == commit` when a remote-tracking ref holds the commit
  (`git for-each-ref --contains`), or when git cannot say; otherwise `pushed` is `False` and
  `linked` is the first of the branch's upstream on a remote that the clone holds, `origin`'s
  branch of the same name and `origin/HEAD`, else the commit. Only refs the clone holds are read.
  `SourceRef.as_dict()` is the data file's `source_ref`; `unpublished_warning(source_ref)` is
  what `docs site` prints on stderr for an unpublished commit, naming
  `git remote set-head origin --auto` when no branch stands in.
- **node_pages.py** — per-node page rendering for `generate.py` (split out to stay under the
  domain-size limit). `render_all_pages(conn, portal=None)` returns sorted `NodePage`s, one per
  node of every kind; each page has summary (through `project_text.render_project_text` with
  `opens_page=False`, so a relative link in it is rebased onto `portal`, or keeps only its text
  with none — BDL-076 `beadloom-ujzb.11`), source, public symbols, a **Relationships** section, linked
  hand-written docs (rooted at `/docs/` so they resolve to the published copy under
  `site/docs/…`), and a **Graph** section that mounts
  `<ArchitectureMap focus="<ref>" :depth="1" height="60vh" />` inside `<ClientOnly>`, the
  architecture viewer opened on the page's node with its card (BDL-076 A4). It replaced the scoped C4/Mermaid diagram, which
  stays on `architecture-diagram.md`; the `ref` is HTML-escaped into the attribute. The
  Relationships section renders OUTGOING
  `part_of`/`depends_on`/`uses` edges as Markdown links to other node pages, then INCOMING
  relationships: **Used by** — the sorted, deduped union of incoming `uses`+`depends_on`
  consumers (who consumes this node; no separate "Depended on by" section) — and **Parts** —
  incoming `part_of` child nodes. Incoming refs are link-safe (a ref with a generated page
  links to it, one without renders as plain text — never a dead link); self-edges are skipped;
  an incoming section with no entries is omitted (a leaf shows neither). Deterministic
  (sorted). `node_page_path(kind, ref_id)` is where a node's page is written (`<dir>/<ref>`,
  under `other/` for a kind with no directory of its own), and `node_page_urls(conn)` maps
  every node of every kind to `/<dir>/<ref>`. The architecture data file links each node
  through it since BDL-076 A1, and both landscape views since A4, when the diagram viewer's
  base-path rewrite learned `/other/`. The landscape map's own URL map, which covered three kinds
  only, is removed.
  `public_symbol_names(conn, ref_id)` lists the public names in the files the node owns; the
  node page lists all of them and the node card the first 50.
- **nav.py** — the generated VitePress nav/sidebar tree builders for `generate.py` (split out
  to keep the generator small). `render_nav_config(conn, project_root)` emits the full
  `.vitepress/config.generated.mjs` module exporting **only** `nav` + `sidebar` (BDL-046
  BEAD-11 dropped VitePress `locales` — its global `/x↔/ru/x` mapping translated the whole menu
  and 404'd off `/ru/` — so there is a single shared EN sidebar and no
  `navRu`/`sidebarRu`/`render_sidebar_ru`). **Top nav is empty** (`render_nav` → `[]`; BDL-046)
  — the VitePress default theme still renders the appearance toggle and local search
  regardless. The **sidebar** (`render_sidebar(conn, *, docs_root, has_getting_started)`) is a
  single ordered, link-safe tree: **About** (`/`) · **Getting Started**
  (`/docs/getting-started`, emitted only if that page exists) · **Dashboard** (flat) ·
  **Architecture** · **Landscape map** (flat) · **Documentation**. The **Architecture** group
  is `collapsed: true` and a `part_of`-nested tree (service root → domains → features) with
  **human-readable** labels via `human_label` (`context-oracle` → `Context Oracle`), roots
  being nodes with no real `part_of` parent (a `root part_of root` self-edge is ignored so the
  root service isn't dropped); an "Architecture overview" entry stays on top and links to
  `/architecture` (the overview page). The **Documentation** group is `collapsed: false`
  (expanded) and mirrors the `docs/` directory tree
  (`render_documentation_group_from_dir(docs_dir, *, collapsed)`) as a nested, collapsible
  structure (each subdir a group, each `.md` a leaf link rooted at `/docs/`), led by an
  Overview link. Dashboard + Landscape map are plain `{ text, link }` entries (not one-child
  groups). Deterministic (sorted, byte-stable); no dead nav links.
- **about.py** — the README→About page (BDL-046; since BDL-076 `beadloom-ujzb.11`, `.12` and
  `.8` a thin front of the project-text path). `portal_links_for(*, published_doc_slugs,
  repository, cross_link_routes=None, base="/", published_files=None)` builds the `PortalLinks`
  every page of the run shares: a README of the pair that `cross_link_routes` routes (e.g.
  `{"readme.ru.md": "/ru/", "readme.md": "/"}`) goes to that route — the in-page bilingual
  toggle that replaced the dropped locale switcher (BDL-046 BEAD-11) — and one it does not route
  is withheld, so a link to it keeps its text. `render_about(readme_text, *,
  published_doc_slugs, repository, cross_link_routes=None)` returns
  `render_project_text(readme_text, portal)`: links follow the rule of `markdown_links`, and the
  text is shown as written (`project_text`). A link to a repository file goes to the DECLARED
  repository's forge route at the generated commit, no longer to `<repo>/blob/main/<path>`.
- **dashboard/** — package (decomposed by cohesion in BDL-059 S4 into `_common`,
  `gate_metrics`, `ai_activity`, `recommendations`, `alerts`, `status_cards`, `assemble`; the
  package `__init__` re-exports the public surface). Showcase A, the AaC/DocAsCode metrics
  dashboard. `build_dashboard_data(conn, *, project_root, federated=None)` returns a
  deterministic, JSON-safe dict and `render_dashboard_md(data)` renders the human page from
  that same dict (the front-end never invents a figure). Honest by construction: every number
  comes from the SAME code path as its gate — `lint` (count + severity breakdown via
  `graph/linter.lint`), `debt` (`debt_report.compute_debt_score` + `compute_debt_trend`,
  serialized via `format_debt_json`), `docs` (coverage % + `sync_state` freshness % + stale
  pair count, read-only), `doctor` (`doctor.run_checks` pass/fail summary), and an optional
  `federated` rollup (per-service edge-verdict health + contract-verdict counts) reusing the
  `federate` output verbatim. It also emits **`trends`** — the recorded time-series from
  `metrics_history.read_history` (sorted by `ts`; ONLY real recorded points — no interpolation,
  no fabricated samples; sparse at first is correct) — **`ai_techwriter`** — the honest "AI
  tech-writer activity" section (G9) read independently from the append-only run-record store
  `.beadloom/ai_techwriter_runs.json` the CI harness emits (absent/empty/corrupt → an
  empty-but-present section, never an error): `runs[]` sorted by `ts` with per-run + cumulative
  docs-refreshed and input/output token spend (ONLY real recorded runs — same no-interpolation
  contract as `trends`), `totals`, and a `cost_estimate` (`{usd, rate_usd_per_1m,
  is_estimate=True, label "est. @ $X/1M tokens"}`) — token counts are FACTS from each record
  while the dollar figure is a clearly-labeled ESTIMATE at the configured `_USD_PER_1M_TOKENS`
  rate, never a hard cost (rendered by the `AiTechwriterActivity` widget). Since BDL-076 B1 the
  section also carries `recorded` (whether `.beadloom/ai_techwriter_runs.json` exists), and
  `render_dashboard_md` mounts `<AiTechwriterActivity />` only when it is `true`, so a project
  that never ran the harness gets no empty panel — and
  **`recommendations`** — a prioritized, actionable list built from the EXISTING gate data (one
  item per lint violation, BREAKING/DRIFT contract risks from the `--federated` artifact, stale
  docs from `sync_state`, and worst-debt nodes from `debt_report` top offenders); each item is
  `{kind, severity, target, message, link}`, severity-ordered (errors first) with deterministic
  tie-breaks, so the panel is honest by construction. For a **critical-first** UX it
  additionally emits **`alerts`** — the attention-banner problems (`{kind, severity, message}`)
  shown IFF there is something wrong (BREAKING contracts → `critical`, DRIFT contracts / lint
  errors / doctor errors → `error`, stale doc-code pairs / high-debt → `warn`/`error`; the
  stale alert reads `N stale pair(s)` since BDL-069 `beadloom-yn6i`, because its count is one
  `sync_state` row per pair and the docs card beside it counts the same rows), severity-ordered
  (BREAKING leads) with deterministic tie-breaks; an empty list is the all-clear state — and
  **`status_cards`** — one threshold-colored card per metric group (`{group, label, status,
  value, detail}` with `status` ∈ `ok`/`warn`/`error`, the severity computed deterministically
  in Python so the front-end only paints the color). `render_dashboard_md` emits only the page
  title + a short intro + the `<ClientOnly>` component mounts (no per-metric text dump, no
  `<noscript>` fallback) — the cards/widgets are the single presentation surface and read the
  honest figures from `dashboard.data.json` (`build_dashboard_data`, unchanged).
- **landscape_map.py** — Showcase B, the 🌟 cross-repo landscape map.
  `build_landscape_data(conn=None, *, federated=None)` returns a deterministic, JSON-safe dict
  (`scope`/`nodes`/`edges`) and `render_landscape_md(data, *, pages=None)` renders a
  **Mermaid** diagram from it (never hand-drawn). With a `federated.json` (the F2 `federate`
  hub output) nodes are the satellites and edges are the cross-repo links carrying the hub's
  `ContractVerdict`-style verdict verbatim; **without it the map is the LOCAL contract graph**
  — `_local_landscape` reads the repo's own `produces`/`consumes` edges, reconciles them by
  `contract_key` into `graph.contracts.Contract`s, classifies each to a `ContractVerdict`, and
  renders one edge per producer→consumer coloured by that verdict (Beadloom's own site emits a
  single `beadloom → vitepress-site` CONFIRMED edge; a repo with no contracts → an empty map).
  This is the real contract reality, not the structural `depends_on`/`uses` arch (which stays
  in the C4 overview). Edges are labelled by their verdict; a Mermaid `classDef` health overlay
  colours nodes (green = healthy, red = broken, grey = external/expected) and broken edges get
  a red `linkStyle`. **Clicks are page-aware**: a node emits `click <id> "/<dir>/<ref>"` ONLY
  when `pages` (from `node_pages.node_page_urls(conn)`) has a real generated page for it. Every
  node of this graph has one, `other/` included; a node with no page (a foreign federated repo)
  renders without a click, so the map never links to a dead page. Every Mermaid id is
  **prefixed** (`n_<sanitized>`) so it can never collide with a reserved keyword (a node named `graph` becomes `n_graph` — the label and click
  route keep the real ref). Since BDL-060 S4 the Mermaid diagram is the **secondary/fallback**
  view (`landscape-diagram.md`); the PRIMARY view is the interactive `landscape_view.py` map.
- **landscape_view.py** — Showcase B PRIMARY view (BDL-060 S4, G2): the interactive
  cross-service landscape. `build_landscape_view_data(conn, *, pages=None)` returns a
  deterministic, renderer-agnostic, JSON-safe dict
  (`schema_version`/`scope`/`nodes`/`edges`/`contracts`) reconciled from the SAME
  `graph.contracts.reconcile_contracts` path the gate/report use — never a re-implemented
  surface — by reconstructing the contract-bearing edge dicts from each edge's `extra.contract`
  blob (mirroring the satellite-export path), so each contract carries its `ContractVerdict`,
  protocol routing (AMQP exchange/routing_key/message_type, or GraphQL schema),
  producer↔consumer endpoints, the named `missing` break paths, what decided the verdict
  (`verdict_basis`, BDL-076 `beadloom-ujzb.6`), and the DEEP field surface: the GraphQL typed
  Tier-A `fields` (`exposed`/`referenced`, S2) OR the AMQP body JSON-Schema
  (`body.exposed`/`referenced`, S3). **Honest degradation**: a contract with no declared
  surface carries an EMPTY `fields`/`body` block (the view renders *undeclared*) — never a
  fabricated field. Nodes carry `kind`/`group`/`health` (worst incident verdict) + a page `url`
  (non-empty only when a real page exists, so a click never resolves to a dead page).
  `serialize_landscape_view(data)` is the byte-stable JSON (`sort_keys`);
  `render_landscape_view_md(data)` renders `landscape.md` — the title + intro + the
  `<ClientOnly><LandscapeMap></ClientOnly>` mount + a static count summary (JS-off fallback) +
  a link to the `landscape-diagram` Mermaid fallback. Its intro names the service card, the
  neighbourhood, **Impact** and the protocol and verdict filters. The rendering lives in the
  VitePress theme: since BDL-076 A4 `LandscapeMap.vue` (the `site-landscape-page` slice) is the
  graph viewer in its landscape mode with the service card in its panel, over the
  `site-landscape-data` slice; see [the site's page](../../../../services/vitepress-site.md).
  ELK runs with fixed seedless options, so layout is deterministic given the byte-stable data.
  The artifact is emitted under `site/public/landscape.data.json` (VitePress copies `public/` to the dist root) for the
  runtime `withBase("/landscape.data.json")` fetch.
- **mermaid_guard.py** — the generation-time Mermaid validity guard (targeted structural
  validators, NOT a full parser). `validate_mermaid(text)` returns a list of `MermaidIssue` for
  the two F4 render bug classes: (1) a flowchart/`graph` node id that equals a reserved Mermaid
  keyword or has an illegal charset; (2) a C4 `Rel(a, b, …)` whose endpoint is not a declared
  `Container`/`Component`/`Person`/`System*` node (a Rel to the boundary/root crashes
  `drawRels`). An extensible validator registry; deterministic (issues in source order).
  `generate.generate_site` calls it on every emitted diagram and raises on any issue.
- **metrics_history.py** — the metrics-history append-store backing honest dashboard trends. A
  tiny additive JSON log at `.beadloom/metrics_history.json` of `MetricsPoint`s (`ts`,
  `lint_violations`, `debt_score`, `coverage_pct`, `sync_pct`, `nodes`, `edges`, `symbols`).
  `append_metrics_point(project_root, point)` records one point per `docs site` run (the `ts`
  is supplied by the caller — never `now()` inside this module — so tests are deterministic;
  appending an existing `ts` overwrites that point so a re-run does not double-count);
  `read_history(project_root)` returns the series sorted by `ts` (only real recorded points,
  never an interpolated one); `backfill_structural_history(conn, project_root)` seeds
  structural counts (nodes/edges/symbols) from the existing `graph_snapshots` history so the
  structural trend isn't empty on day one (idempotent; never overwrites a richer recorded
  point). Additive append-state, NOT a versioned artifact — no schema bump.
- **published_docs.py** — Showcase C, the published validated documentation.
  `publish_docs(conn, out_dir, *, project_root, portal=None)` copies the REAL `docs/**` tree
  into `out_dir/docs/…` preserving structure. Since BDL-076 `beadloom-ujzb.11` and `.12` each
  Markdown copy goes through `project_text.render_project_text`: a link that leaves `docs/` is
  rebased onto `portal` (with none it keeps only its text), a link inside `docs/` to a file the
  portal does not publish becomes its text, and what Vue would read is made inert, so the
  authored prose is no longer copied byte for byte. `published_files(project_root)` lists the
  project paths of every file it copies. It injects a
  per-doc validation badge into the COPY only — the source `docs/` is NEVER mutated (no AI
  prose-rewriting; that is the deferred F4.1). A generated `docs/index.md` landing page (sorted
  links to every published doc) is also emitted so the `/docs/` nav target resolves.
  `build_published_docs(conn, *, project_root)` returns the deterministic per-doc inputs
  (`PublishedDoc`: `status`/`reason`/`synced_at`/`ref_id`/`coverage_pct`); the status comes
  from the `doc_sync` engine via `check_sync` — the SAME code path `beadloom sync-check` runs —
  so a doc the gate calls stale shows `stale` on the site. The badge head is `✅ fresh` /
  `⚠️ stale — <reason>` for tracked docs; a doc tracked by NO doc-code pair is badged **neutrally**
  as `📘 reference — overview/guide, not tied to a code symbol` (an overview/guide is not a
  defect, so it is NOT called "untracked"). `inject_badge(prose, badge_body)` wraps the badge
  between the stable `<!-- beadloom:badge-start -->` / `-end -->` markers, below a closed
  front matter that gray-matter reads (BDL-076 `beadloom-ujzb.21`: VitePress reads front matter
  only at the very top of a page; `beadloom-ujzb.23`, m1: a block gray-matter cannot parse
  would fail the build there, so the badge then goes first and the block below it is shown as
  Markdown), so regeneration overwrites ONLY the badge region;
  `render_published_doc(doc, prose)` renders the badged Markdown. Fresh/stale badges show `last
  synced` (the stored `sync_state.synced_at`, not wall-clock → deterministic) and the owning
  node's read-only source-coverage %; the **reference** (untracked) badge deliberately omits
  the coverage % line — that figure is the node's source coverage, unrelated to the prose, and
  printing it next to a not-tracked doc reads as a contradiction.

The dashboard's not-fresh count and a node's stale marker read
`status IN ('stale','missing')`: a pair whose file is gone is not one less thing
to worry about (BDL-UX #174).

### The architecture data file, schema version 2

`architecture.data.json` is a contract between this feature and the viewer. BDL-076 A1 raised
its `schema_version` to 2 and kept every key of version 1 with its meaning. The viewer's
`site-architecture-data` slice accepts versions 1 and 2 and refuses any other with a message on
the page. Since A3 the viewer reads the version-2 fields: the declared layers, the node card, and
the findings, tests and docs the node status and the impact mode read. The static site shows
all of it without querying the index.

**Top level.** `schema_version`, `scope` (`architecture`), `nodes` and `edges`, and since
version 2:

- `generated_at` — the run's `now_ts`, so a fixed instant regenerates byte for byte;
- `beadloom_version`;
- `layers` — the declared layers of the first `layers` rule by name, top to bottom, each
  `{name, rank, tag, token}`, where `token` is what a node in that layer carries as its `layer`
  (the tag with its `layer-` prefix removed);
- `layer_order` — the direction that rule enforces, `""` when none is declared;
- `layer_rules` (BDL-080 S1b, S1e) — every `layers` rule the index holds, ordered by name, each
  `{name, title, scope, edge_kind, layers}`. `title` is the rule's declared `title:`, `""` when
  it declares none. `scope` is the declared `scope:`, else the derived one (the lowest container
  holding every node the rule places a layer on), else `""`. `layers` is the rule's layers top
  to bottom, each `{name, rank, tag, token}`, where `token` is the layer's NAME (`services`,
  `widgets`), unlike `layers[].token` above (`service`). `[]` when no layer rule is declared.

**The original layer keys describe the first rule, inside its scope.** `layers`, `layer_order`
and each node's `layer` and `layer_rank` keep the meaning they had in schema 2 before every rule
was written: the first `layers` rule by name. Since BDL-080 S1f that rule is read inside its
`scope:`, as the linter reads it. A node outside the scope has `layer` `""` and `layer_rank`
`null` even when it carries one of the rule's tags, and a `depends_on` edge between nodes no rule
places carries no `violation` key. A project whose first rule declares no `scope:` gets output
byte-identical to the build before S1f (measured on the six adopter fixtures). The node card's
`tags` stay what the node declares, scope or not.

Nothing derived from the git remote is at the top level. A1 wrote a `project` name and A3 a
`repository {url, ref}`; no screen read either, and a remote could carry a credential or a
`?token=` into both, so the re-review removed them (`beadloom-ujzb.10`). The remote reaches the
file only as each node's `source_url`, and only when the project declares no `site.repo_url`.

**Per node.** Version 1: `id`, `label`, `kind`, `summary`, `layer`, `layer_rank`, `group`,
`symbols`, `doc_status`, `doc_links`, `url`, `parent`, `depends_on`, `depended_on_by`, `uses`,
`used_by`, and `lint_clean` when lint ran. `url` comes from `node_pages.node_page_urls`, so every
node links to its page, `other/` included. Since BDL-080 S1b every node also carries:

- `layer_rule` — the name of the rule that places the node (`LayerRulesView.placement`), `""`
  when no rule does;
- `layer_rule_rank` — the node's rank in that rule's layers, `null` when no rule places it.

On this repository `site-graph-viewer` reads `layer_rule` `site-fsd-layers`, `layer_rule_rank`
2, while its `layer` stays `""` and its `layer_rank` 0 under the first rule.

Version 2 adds the card:

| Key | Shape | Absent or empty when |
|---|---|---|
| `source` | the declared source | `""` when the node declares none |
| `source_url` | the finished link to `source` at the commit the site was generated from, by the forge's own route | `""` with no source, no git repository of the project's own, no declared `site.repo_url` and a remote a browser cannot open, or a host that is neither a public forge's nor declared in `site.forges` |
| `lifecycle` | the node's lifecycle | — |
| `tags` | sorted list | `[]` |
| `docs` | `[{path, status}]` — the worst status of the doc's sync pairs (`missing`, `stale`, `unverified`, `ok`), `unpaired` for a doc with no pair | `[]` |
| `tests` | `{files, file_count, count, placement}` | `null` when the test binding does not cover the node |
| `public_symbols` | `{names, omitted}` — the first 50 public names and how many more | — |
| `activity` | `{commits_30d, lines_30d, level}`, the keys of the activity the reindex recorded that the card shows | `null` when none was recorded, as on a shallow clone that does not reach back 90 days |
| `findings` | `[{rule, severity, message}]` from `beadloom lint` | omitted when lint did not run |
| `debt` | `{score, reasons}` from the debt report | `{score: 0.0, reasons: []}` for a node the report does not score; omitted when not computed |

`lint_clean` is now the version-1 reading of `findings`: true when the list is empty. The viewer
draws a node as a violation only for a finding of severity `error`.

**`activity` is an allow-list.** The reindex records the level, commits and changed lines in 30
and 90 days, the last commit date and the names of the node's most frequent committers. The data
file is published, and the card shows three of those, so `CARD_ACTIVITY_KEYS` names the three
(`commits_30d`, `lines_30d`, `level`; `lines_30d` added by BDL-078 F-activity, schema still 2)
and nothing else reaches the file (BDL-076 R1 finding M2). `level` is one of `hot`, `warm`,
`cool`, `quiet`, `dormant`, relative to the project; the card shows an unknown level as text. The contract test pins the allow-list, and the
`node_card_data` scenarios check that no generated file names the project's commit author and
that a credential written into the remote reaches none.

**A test file is listed at the node it is bound to (BDL-076 K4).** `tests.files` names only the
files whose `test_files` owner is this node. A file whose owner the graph does not hold stays
listed where it is counted, since no other node would list it. `file_count` (new in K4), `count`
and `placement` are taken over the node and its `part_of` descendants, the same files
`beadloom ctx` counts, so a container shows the numbers it showed before. Listed at every
ancestor, the paths were the largest field of the file. Measured by K4 on this repository: the
file went from 376,794 to 331,941 bytes (gzip 44,755 to 38,711), and the listings from 877 to
299, one per distinct file. The schema version stayed 2.

**Edges.** One per `part_of`, `depends_on`, `uses`, `consumes` and `produces` edge, sorted. A
contract edge (`consumes`/`produces`, new in version 2) carries its `contract` key, so two
contracts between one pair of nodes stay two edges. A `depends_on` edge carries `violation` when
a rule judged it: the first rule by name ranks both ends inside its scope, or any `depends_on`
rule places a layer at both ends. Its value is `true` when any rule finds against the edge.
An edge no rule judged carries no `violation` key, never `false`. `touches_code` stays out: it
points at a file, not at a node.

Every key BDL-080 added is additive, and `schema_version` stays 2. A version-2 file written
before it carries no `layer_rules`, `layer_rule` or `layer_rule_rank`, and the viewer then reads
the first rule's `layers` and `layer_rank` as before.

### The landscape data file

`landscape.data.json` is written by `landscape_view.py` and read by the viewer's
`site-landscape-data` slice. Its `schema_version` is 1; `verdict_basis` was added to it without
a bump, because a reader that does not know the key loses nothing.

- **Top level:** `schema_version`, `scope` (`product`), `nodes`, `edges`, `contracts`.
- **Node** (a contract's producers and consumers only): `id`, `label`, `kind`, `group`,
  `health` (the worst verdict among its contracts: `broken`, `neutral` or `healthy`) and `url`,
  the node's page from `node_page_urls`.
- **Edge:** `src` (a producer), `dst` (a consumer), `verdict` and `contract_key`, one per
  producer and consumer pair of each contract, a self-loop dropped.
- **Contract:** `contract_key`, `protocol`, `name`, `verdict`, `verdict_basis`, `lifecycle`,
  `routing`, `producers`, `consumers`, `missing`, `fields {exposed, referenced}` and
  `body {exposed, referenced}`.

`verdict_basis` states what decided the verdict. `lifecycle` is a verdict the declared lifecycle
decides before any comparison (`external`, `dead`, `expected`). `surface` is a `breaking`
verdict, or a `confirmed` one that compared the two sides: two AMQP bodies, typed GraphQL fields
on both sides, or the names a GraphQL consumer references. Anything else is `presence`: only
which sides exist was checked. A GraphQL comparison by name leaves no other trace in the file,
so the generator, which ran the reconciliation, states it. The viewer calls a contract that is
neither broken nor decided by its surface "unverified". This repository's one contract,
`site-data:site-bundle` from `beadloom` to `vitepress-site`, is `confirmed` on `presence`.

### Output contract

The generated `site/` tree is consumed by the VitePress site (the
`vitepress-site` node) — a real producer → consumer contract. Since BDL-076 B1 the consumer's
files are written into the same directory by the same run: the scaffold from the installed
package, `.vitepress/site.generated.mjs` beside the nav's `.vitepress/config.generated.mjs`, and
`.beadloom/site/` last. The shipped `.vitepress/config.mjs` and the browser tests read both
generated modules through `.vitepress/generated.mjs` (`importGenerated`): a module that is not
there yet loads as `{}` with a console warning, and any other load error is thrown, because a
portal built without its identity deploys under the wrong base and says nothing. The source `docs/`
is never written; output goes only under `--out` (default `site/`). The run's
instant comes from `now_ts`, injected in tests for determinism and defaulting to
the current UTC instant in production. It is the only wall-clock read, and it
lands in two places: the metrics point recorded in the append-only history store
and the `generated_at` field of `architecture.data.json`. No dashboard field
carries it.

## Invariants

- Generation is deterministic and read-only over the graph; a fixed `now_ts` regenerates the
  tree byte for byte.
- The source `docs/` is never modified; only `--out` is written.
- The Mermaid guard validates every emitted diagram at generation time, so a
  broken diagram fails the build rather than the published site.
- `architecture.data.json` version 2 keeps every key of version 1 with its meaning. The keys of
  both versions are pinned by
  `tests/integration/application/site/architecture_view/test_the_data_file_carries_the_node_card.py`.
- A value the run did not compute is omitted, never reported clean.
- Nothing from the git remote is published except each node's `source_url`, and a source link
  is written only for a forge recognised by its public host or declared in `site.forges`, never
  guessed. The project's own text links to repository files only when `site.repo_url` is
  declared.
- A file in the output directory that beadloom did not write, or that was edited after it was
  written, is never overwritten by the scaffold or the Pages workflow.
- Nothing that ships in the scaffold names a node, bead or path of this repository: graph
  annotations are stripped at write time, and a self-check reads every node id and the tracker.
- A `site:` value the portal cannot use stops `docs site` before any file is written.
- Beadloom's own repository appears in a portal only as the footer's link to it (BDL-080 S4d).
  The footer's component ships either way; `site.powered_by: false` keeps it from rendering.
- `activity` in the data file carries only the keys in `CARD_ACTIVITY_KEYS`.
- `layers`, `layer_order`, `layer` and `layer_rank` describe the first `layers` rule by name,
  inside its `scope:`; every other rule reaches the file through `layer_rules`, `layer_rule`
  and `layer_rule_rank`. An edge carries `violation` only when a rule judged both ends.

## API

Module `src/beadloom/application/site/generate.py`:
- `SiteResult` — frozen dataclass: `out_dir`, `written` (sorted tuple of every written path),
  `scaffold` (`ScaffoldReport`)
- `MermaidValidationError` — raised when a generated page fails the Mermaid guard (carries
  `page` + `issues`)
- `generate_site(conn, out_dir, *, project_root, federated=None, now_ts=None)` -> `SiteResult`
  — deterministic VitePress tree generator; never writes into the source `docs/`; guards every
  emitted diagram; raises `SiteConfigError` before writing when the `site:` block is refused.
  Emits the About home `index.md` from `README.md` (fallback: architecture overview), the architecture overview at `architecture.md`, a RU About `ru/index.md` from
  `README.ru.md` (skipped when absent; both link to each other via the in-page `/` ↔ `/ru/`
  cross-link), and a `docs/index.md` Documentation overview = intro + per-section named-members
  descriptions, no link wall (BDL-046 BEAD-11). `now_ts` is the injected ISO-8601 instant of
  the run: it stamps the metrics-history point and `architecture.data.json`'s `generated_at`
  (deterministic in tests; defaults to the current UTC instant in production, the only
  wall-clock read). The package `__init__` re-exports it, so `from beadloom.application.site
  import generate_site` is the entry the CLI uses.

Module `src/beadloom/application/site/mermaid_guard.py`:
- `MermaidIssue` — frozen dataclass: `kind` (`reserved-id`/`charset`/`c4-rel-undeclared`),
  `message`
- `validate_mermaid(text)` -> `list[MermaidIssue]` — targeted structural guard for flowchart
  reserved-id/charset + C4 Rel integrity (extensible, deterministic)

Module `src/beadloom/application/site/dashboard/` (package; public surface re-exported from
`__init__`):

- `build_dashboard_data(conn, *, project_root, federated=None)` -> `dict` — deterministic
  dashboard data (lint/debt/docs/doctor + optional federated rollup + critical-first `alerts` +
  threshold-colored `status_cards` + `trends` time-series + prioritized `recommendations`);
  honest by construction (reuses each gate's code path; trends are exactly the recorded points)
- `render_dashboard_md(data)` -> `str` — render `dashboard.md` from the data dict: the page
  title + a short intro + the `<ClientOnly>` block mounting the banner + status cards
  (`<AlertBanner/>`/`<StatusCards/>`) and the committed ECharts widgets
  (`<HealthGauges/>`/`<CategoryChart/>`/`<TrendCharts/>`/`<Recommendations/>`,
  theme-registered, reading `dashboard.data.json`). No per-metric text dump, no `<noscript>`
  fallback — the widgets are the single presentation surface (data honesty lives in
  `dashboard.data.json`)
- `serialize_dashboard_data(data)` -> `str` — deterministic JSON (sorted keys) for
  `dashboard.data.json`

Module `src/beadloom/application/site/metrics_history.py`:
- `MetricsPoint` — frozen dataclass: `ts`, `lint_violations`, `debt_score`, `coverage_pct`,
  `sync_pct`, `nodes`, `edges`, `symbols`
- `history_path(project_root)` -> `Path` — `.beadloom/metrics_history.json`
- `append_metrics_point(project_root, point)` — append/overwrite-by-ts and persist (injected
  ts; idempotent per ts)
- `read_history(project_root)` -> `list[MetricsPoint]` — the recorded series sorted by `ts`
  (only real points, no fabrication)
- `backfill_structural_history(conn, project_root)` — seed structural counts from
  `graph_snapshots` (idempotent; never clobbers a recorded point)

Module `src/beadloom/application/site/landscape_map.py`:
- `build_landscape_data(conn=None, *, federated=None)` -> `dict` — deterministic landscape-map
  data (`scope`/`nodes`/`edges`); federated when a `federate` artifact is given, else a
  single-repo **contract** map from the local graph (`produces`/`consumes` edges reconciled by
  `contract_key` into `Contract`s, classified to a `ContractVerdict`; one edge per
  producer→consumer)
- `render_landscape_md(data, *, pages=None)` -> `str` — render `landscape.md` as a Mermaid
  diagram (verdict-labelled edges, `classDef` health overlay, clickable nodes); never
  hand-drawn. `pages` is a `ref_id → existing page URL` map: a node emits a `click` ONLY when
  it has a real generated page, so the map never links to a dead URL (a foreign federated repo
  renders without a click)

Module `src/beadloom/application/site/landscape_view.py`:
- `build_landscape_view_data(conn, *, pages=None)` -> `dict` — deterministic, renderer-agnostic
  interactive-landscape data (`schema_version`/`scope`/`nodes`/`edges`/`contracts`); contracts
  reconciled via `graph.contracts.reconcile_contracts` from each edge's `extra.contract` blob,
  carrying verdict/`verdict_basis`/routing/producers/consumers/`missing` + the GraphQL typed
  `fields` (S2) or
  AMQP `body` JSON-Schema (S3); empty surface → *undeclared* (no fabrication). `pages` gives a
  node a non-empty `url` only when a real page exists
- `serialize_landscape_view(data)` -> `str` — byte-stable JSON (`sort_keys`, 2-space, trailing
  newline)
- `render_landscape_view_md(data)` -> `str` — render the primary `landscape.md`: title + intro
  + `<ClientOnly><LandscapeMap></ClientOnly>` mount + a static JS-off count summary + a link to
  the `landscape-diagram` Mermaid fallback (pure function of `data`)

Module `src/beadloom/application/site/node_pages.py`:
- `NodeRow` / `NodePage` — frozen dataclasses for a graph node and its rendered page
- `load_nodes(conn)` -> `list[NodeRow]`; `render_all_pages(conn, portal=None)` -> sorted
  `list[NodePage]`, one per node; `render_node_page(conn, node, kinds, portal=None)` ->
  `NodePage`, whose summary is project text and whose last section mounts `ArchitectureMap`
  focused on the node
- `node_page_path(kind, ref_id)` -> `str` — the page's path without `.md`, `other/` for a kind
  with no directory
- `node_page_urls(conn)` -> `dict[str, str]` — every node's page URL, every kind included; the
  architecture data file and both landscape views link through it
- `public_symbol_names(conn, ref_id)` -> `list[str]` — the public names in the files the node
  owns, sorted

Module `src/beadloom/application/site/nav.py`:
- `human_label(ref_id)` -> `str` — title-cased, hyphen→space label (`context-oracle` → `Context
  Oracle`)
- `render_architecture_group(conn)` -> `str` — the collapsed, `part_of`-nested Architecture
  sidebar group (human labels; self-edge-safe roots; "Architecture overview" → `/architecture`)
- `render_documentation_group(project_root)` -> `str` — the Documentation sidebar group
  mirroring the `docs/` tree (nested, collapsible; `/docs/`-rooted leaf links)
- `render_documentation_group_from_dir(docs_dir, *, collapsed)` -> `str` — the Documentation
  group from a docs dir with an explicit `collapsed` flag (expanded on the site)
- `render_nav()` -> `str` — the top-nav JS array, intentionally `"[]"` (BDL-046; theme keeps
  appearance toggle + local search)
- `render_sidebar(conn, *, docs_root, has_getting_started)` -> `str` — the full ordered,
  link-safe sidebar (About / Getting Started / flat Dashboard / Architecture / flat Landscape
  map / expanded Documentation)
- `render_nav_config(conn, project_root)` -> `str` — the full deterministic
  `.vitepress/config.generated.mjs` module: exports **only** `nav` (empty) + the single shared
  `sidebar`. VitePress `locales` was dropped (BDL-046 BEAD-11), so there is no
  `navRu`/`sidebarRu`/`render_sidebar_ru`

Module `src/beadloom/application/site/about.py`:
- `portal_links_for(*, published_doc_slugs, repository, cross_link_routes=None, base="/",
  published_files=None)` -> `PortalLinks` — what the portal publishes, the README pair routed or
  withheld
- `render_about(readme_text, *, published_doc_slugs, repository, cross_link_routes=None)` ->
  `str` — the README as the About page body, through `render_project_text`

Module `src/beadloom/application/site/site_config.py`:
- `SITE_KEY` — `"site"`; `SiteConfig(title, description, base, repo_url, forges, logo="",
  powered_by=True, repo_icon="")`; `SiteConfigError(refusals)`
- `read_site_config(project_root)` -> `tuple[SiteConfig, tuple[Refusal, ...]]`;
  `site_config_of(project_root)` -> `SiteConfig` (raises on any refusal)
- `canonical_repo_url(url)` -> `str`; `render_site_module(config, project_root)` -> `str`;
  `unlinked_repository(project_root)` -> `str`

Module `src/beadloom/application/site/repository_icon.py`:
- `repo_icon_of(repo_url, forges=None, declared="")` -> `str`; `REPO_ICONS`; `GENERIC_ICON`

Module `src/beadloom/application/site/site_logo.py`:
- `read_logo(value, where)` -> `tuple[object, tuple[Refusal, ...]]`;
  `logo_problem(project_root, logo, where)` -> `Refusal | None`; `logo_site_path(logo)` -> `str`;
  `copy_logo(project_root, logo, out_dir)` -> `Path | None`; `is_monochrome(project_root, logo)`
  -> `bool`; `LOGO_SUFFIXES`

Module `src/beadloom/application/site/favicon.py`:
- `uses_beadloom_favicon(project_root, logo)` -> `bool`; `favicons_of(project_root, logo)` ->
  `list[dict[str, str]]`; `write_beadloom_favicon(out_dir)` -> `list[Path]`; `LIGHT_GLYPH`;
  `DARK_SCHEME_GLYPH`; `DARK_SCHEME`; `FAVICON_PNG_SIZE`

Module `src/beadloom/application/site/source_ref.py`:
- `SourceRef` — frozen dataclass `commit`, `linked`, `pushed`; `on_branch` -> `bool`;
  `as_dict()` -> `dict[str, object]`
- `source_ref_of(project_root, commit)` -> `SourceRef`; `unpublished_warning(source_ref)` ->
  `str | None`; `SHORT_COMMIT` (12)

Module `src/beadloom/application/site/forge_routes.py`:
- `Forge(kind, tree, blob, raw)` with `link(route, url, ref, path)` and `route_segments`;
  `KNOWN_FORGES`; `PLACEHOLDERS` — `("url", "ref", "path")`
- `on_branch(forge)` -> `Forge` — the forge's routes naming a branch: Gitea's `src/branch/` and
  `raw/branch/`, Azure DevOps' `GB` and `versionType=branch`; any other forge as it is
- `forge_for(web_url, declared=None)` -> `Forge | None`; `read_forge(setting)` ->
  `tuple[Forge | None, tuple[str, ...]]`; `template_problem(template)` -> `str | None`;
  `runs_past_repository(web_url, forge)` -> `bool`; `stops_before_repository(web_url, forge)` ->
  `str | None` (the forge's repository shape when the address stops before one)

Module `src/beadloom/application/site/scaffold.py`:
- `SCAFFOLD_PACKAGE_DIR`, `OVERRIDE_DIR`, `MARKABLE_SUFFIXES`; `ScaffoldError`
- `Marker`, `Placement`, `KeptFile`, `ScaffoldReport` — frozen dataclasses
- `write_scaffold(out_dir, *, project_root, version, source=None)` -> `ScaffoldReport`
- `shipped_files(source=None)` -> `dict[str, str]`; `without_annotations(body)` -> `str`
- `mark(rel, body, version)` -> `str`; `read_marker(text)` -> `Marker | None`;
  `marker_line(body, version, note)` -> `str`; `place_marked(target, expected)` -> `Placement`

Module `src/beadloom/application/site/pages_workflow.py`:
- `PAGES_WORKFLOW_PATH`; `PagesWorkflowError`; `PagesWorkflowReport`
- `write_pages_workflow(project_root, *, out_dir, base, version, source=None, branch=None)` ->
  `PagesWorkflowReport`; `render_pages_workflow(*, base, site_dir, node_major, version,
  branch="")` -> `str`
- `node_major_of(engines_node)` -> `str`; `site_dir_of(project_root, out_dir)` -> `str`;
  `default_branch_of(project_root)` -> `str`

Module `src/beadloom/application/site/pages_base.py`:
- `project_pages_base(remote)` -> `str | None`; `base_warning(base, remote)` -> `str | None`

Module `src/beadloom/application/site/markdown_links.py`:
- `PortalLinks(doc_slugs, page_routes, repository, withheld, base, mirrored_files)` with
  `route_of(path)`, `page_url(route)`, `publishes(path)`, `repository_url_of(path, *, image=False)`
- `rebase_links(markdown, portal, *, source_dir="", mirrored_dir="", page_dir=None,
  front_matter=True)` -> `str`
- `raw_html_destination(url, portal, *, source_dir="", mirrored_dir="", page_dir=None,
  asset=False)` -> `str | None`

Module `src/beadloom/application/site/project_text.py`:
- `render_project_text(markdown, portal, *, source_dir="", mirrored_dir="", page_dir=None,
  opens_page=True)` -> `str`

Modules `vitepress_markdown.py`, `markdown_positions.py`, `markdown_source.py`,
`markdown_attrs.py`, `raw_html.py`:
- `vitepress_markdown()` -> `MarkdownIt`; `front_matter_length(text, *, closed_only=False)` ->
  `int`; `front_matter_is_read(text)` -> `bool`; `CONTAINERS`, `TITLED_CONTAINERS`
- `located_markdown()` -> `MarkdownIt`; `normalise(text)` -> `str`
- `read_markdown(text, *, front_matter=True)` -> `MarkdownSource`; `Edit`,
  `apply_edits(source, edits)` -> `str`; `Segment`, `Element`, `RawHtml`, `Text`, `CodeSpan`,
  `CodeBlock`, `Autolink`, `RawLabel`, `Link`, `Definition`, `CodeRegion`
- `attribute_braces(text, *, opens, closes, alone)` -> `list[int]`;
  `ends_with_attributes(text)` -> `bool`
- `read_markup(html)` -> `list[Markup]`; `Markup`, `Attribute`

Module `src/beadloom/application/site/published_docs.py`:
- `BADGE_START` / `BADGE_END` — stable markers delimiting the injected badge region
- `PublishedDoc` — frozen dataclass: `doc_path`, `status`, `reason`, `synced_at`, `ref_id`,
  `coverage_pct`
- `build_published_docs(conn, *, project_root)` -> `list[PublishedDoc]` — per-doc validation
  inputs from `check_sync` (same source as `sync-check`); a doc with no doc-code pair is
  `untracked` and rendered as a neutral `📘 reference` badge (no coverage % line)
- `inject_badge(prose, badge_body)` -> `str` — marker-delimited badge prefix, below front matter
  gray-matter reads and above any other; re-injection overwrites only the badge region
- `render_published_doc(doc, prose)` -> `str` — badged Markdown (badge + the prose given)
- `published_files(project_root)` -> `frozenset[str]` — the `docs/…` paths `publish_docs` copies
- `publish_docs(conn, out_dir, *, project_root, portal=None)` -> `list[Path]` — copy `docs/**`
  into `out_dir/docs/…`, each Markdown copy through `render_project_text`, with badges (plus a generated `docs/index.md` landing page so the `/docs/`
  nav target resolves); never mutates the source

Module `src/beadloom/application/site/architecture_view.py`:
- `ARCHITECTURE_SCHEMA_VERSION` — `2`
- `build_architecture_view_data(conn, *, pages=None, published_doc_slugs=None, verdicts=None,
  generated_at="", repository=None)` -> `dict` — the data file described above. `pages` gives a
  node a non-empty `url` only when present; `published_doc_slugs` gates the doc links (`None`
  skips the gate); a `verdicts` field left `None` is omitted from every node; `repository` is
  the `RepositoryLink` each node's `source_url` is built from, and `None` gives every node an
  empty link. Until A1 the lint input was `lint_violation_refs`, a set of node ids; it is
  replaced by `verdicts`. The `project` parameter was removed with the top-level key.
- `serialize_architecture_view(data)` -> `str` — byte-stable JSON (`sort_keys`)
- `render_architecture_view_md(data)` -> `str` — the `architecture.md` page

Module `src/beadloom/application/site/layer_rules_view.py` (BDL-080 S1b):
- `FLAGGED_EDGE_KIND` — `"depends_on"`, the edge kind the view renders a layering verdict on
- `declared_layer_rules(conn)` -> `tuple[LayerRule, ...]` — every `layers` rule in the index,
  ordered by name; an unreadable row is skipped and logged
- `RulePlacement` — frozen dataclass `rule`, `rank`
- `LayerRulesView` — frozen dataclass `rules`, `parents`, `scoped_tags` (per rule, the tags
  inside its scope); `declared(ref_ids)` -> `list[dict]` (the `layer_rules` key),
  `placement(ref_id)` -> `RulePlacement | None`, `judges(src, dst)` -> `bool`,
  `flagged(conn)` -> `frozenset[tuple[str, str]]`
- `layer_rules_view(rules, parents, tags)` -> `LayerRulesView`

Module `src/beadloom/application/site/architecture_card.py`:
- `PUBLIC_SYMBOL_CAP` — `50`; `DOC_UNPAIRED` — `"unpaired"`; `CARD_ACTIVITY_KEYS` —
  `("commits_30d", "lines_30d", "level")`
- `NodeFinding` — frozen dataclass `rule`, `severity`, `message`; `as_dict()`
- `NodeVerdicts` — frozen dataclass `findings`, `debt`; `None` means not computed
- `CardSources` — frozen dataclass `tags`, `placements`, `test_owners`, `verdicts`,
  `repository` (an empty `RepositoryLink` by default)
- `card_sources(conn, *, tags, verdicts, repository=None)` -> `CardSources`
- `card_fields(conn, ref_id, *, source, lifecycle, raw_extra, sources)` -> `dict`
- `doc_pairs(conn, ref_id)` -> `list[dict]` — each doc of the node with its worst pair status
- `bound_tests(extra, sources, ref_id)` -> `dict | None` — the `tests` field
- `capped_public_symbols(conn, ref_id)` -> `dict` — `{names, omitted}`
- `card_activity(recorded)` -> `dict | None` — the recorded activity narrowed to
  `CARD_ACTIVITY_KEYS`; `None` when none was recorded

Module `src/beadloom/application/site/repository_link.py`:
- `RepositoryLink` — frozen dataclass `url`, `ref` (both `""` when nothing states them),
  `forges`, `source` (the `SourceRef`, `None` without a commit or an address); `source_url(source)`, `file_url(path)`, `raw_url(path)` -> `str` — the forge's
  `tree`, `blob` and `raw` routes at `ref`, `""` when there is no repository, commit or path, or
  no forge is known for the host. `forge_of` was removed; `forge_routes.forge_for` replaces it
- `web_url_of_remote(remote)` -> `str` — the web address of a git remote, `""` when a browser
  cannot open it or the remote cannot be parsed; never raises
- `origin_remote(project_root)` -> `str` — the `origin` remote as git records it, `""` when none
- `repository_of(project_root, *, declared_url="", forges=None)` -> `RepositoryLink` — the
  declared repository, else `origin`, and the current commit, which is empty unless
  `project_root` is the top of its own git repository

## Testing

Tests bound to this node (the binding moved with the package in K1):
`tests/integration/application/site/` — `test_architecture_view.py`,
`test_the_view_flags_what_the_rule_finds.py`, `test_site_landscape.py`,
`test_site_metrics_history.py`, `test_site_nav.py`,
`test_a_node_page_opens_the_viewer_on_its_node.py` (A4),
`test_every_landscape_node_links_to_its_page.py` (A4), and
`architecture_view/test_the_data_file_carries_the_node_card.py` (A1, K4, the source link and
the activity allow-list),
`architecture_view/test_the_view_ranks_nodes_by_the_declared_layers.py`, and since BDL-080
`architecture_view/test_the_data_file_carries_every_layer_rule.py` (`layer_rules`, placement,
the derived scope, the union verdict, a scoped first rule, the rule's title) and
`architecture_view/test_the_six_fixtures_keep_every_existing_layer_key.py` (the data files of
the six adopter fixtures that predate the FSD ones, `SIX_STACKS`, the new keys stripped,
identical to the build before S1b; `vue-fsd` and `rn-fsd` have no build before to compare);
and `tests/unit/application/site/` — `test_site_about.py`, `test_site_mermaid_guard.py`,
`test_a_remote_becomes_the_web_address_of_its_repository.py` and
`test_a_source_links_to_its_forge_or_not_at_all.py` (the remote and the forge routes), and
`test_a_contract_names_what_decided_its_verdict.py` (`verdict_basis`), and
`layer_rules_view/test_an_unreadable_layer_rule_row_leaves_the_others_drawn.py` (BDL-080 S1T).

Slice 2 (BDL-076 B1–B4, `beadloom-ujzb.8`, `.11`–`.13`, `.18`, `.20`, `.21`), under
`tests/unit/application/site/`: the `site:` block and the forges
(`test_the_portal_takes_its_identity_from_the_site_block.py`,
`test_the_site_block_declares_a_forge_per_host.py`,
`test_the_header_icon_follows_the_host_or_the_declared_icon.py` and
`test_the_project_logo_is_checked_and_copied.py` (BDL-080 S4d),
`test_beadloom_favicon_png_is_the_light_scheme_glyph.py` (BDL-080 S4e),
`test_a_declared_repository_address_is_read_in_one_spelling.py`, which since
`beadloom-ujzb.23` also holds the `repo_url` refusals by forge shape,
`test_a_self_hosted_forge_links_by_the_kind_the_project_declares.py`,
`test_the_declared_repository_wins_over_the_remote.py`,
`test_a_repository_file_in_project_text_follows_its_forge.py`), the scaffold
(`test_the_scaffold_is_written_once_and_never_over_a_hand_edit.py`), the Pages workflow and the
base (`test_the_pages_workflow_deploys_the_portal_and_keeps_a_hand_edit.py`,
`test_the_pages_workflow_grants_each_job_only_what_it_needs.py`,
`test_a_default_base_is_warned_about_on_a_github_project_repository.py`), and project text
(`test_a_link_in_project_text_is_rebased_or_kept_as_text.py`,
`test_a_raw_html_link_follows_the_link_rule.py`, `test_markdown_is_parsed_as_vitepress_parses_it.py`,
`test_project_text_is_read_as_vitepress_reads_it.py`,
`test_project_text_is_shown_as_written_not_compiled_by_vue.py`,
`test_braces_markdown_it_attrs_would_read_are_shown_as_written.py` (`beadloom-ujzb.23`),
`test_where_code_is_in_project_markdown.py`); under `tests/integration/application/site/`:
`test_the_scaffold_ships_with_the_package.py`,
`test_the_written_scaffold_names_none_of_this_repositorys_nodes.py`,
`test_config_check_reads_the_site_block.py`,
`test_a_generated_module_that_fails_to_load_is_not_read_as_missing.py`,
`test_project_text_on_a_page_is_not_a_vue_template.py`,
`test_project_text_on_a_page_leaves_no_dead_link.py`, and the slow adopter builds, skipped unless
`BEADLOOM_RUN_SLOW=1` and run by the `site-adopters` workflow:
`test_an_adopter_builds_its_portal_from_docs_site.py`,
`test_an_adopter_portal_on_every_claimed_stack.py` (eight fixtures under `tests/fixtures/site/`:
python, go, typescript, java, kotlin, swift, and since BDL-080 S3d the Feature-Sliced frontends
`vue-fsd` and `rn-fsd`, whose layers and rules `init` writes with no hand edit)
and `test_the_browser_tests_pass_on_an_adopter_portal.py`. The two FSD fixtures have a fast test
of their own, `test_an_fsd_adopter_fixture_is_judged_by_the_rules_init_writes.py` (the import
forms each fixture carries, its planted findings, the Expo bridges). The `site-adopters` matrix
has nine legs, `[python, go, typescript, java, kotlin, swift, vue-fsd, rn-fsd, projects]`,
reported as the check runs `site-adopters (<part>)`. That workflow starts on a pull request
only through its `paths:` filter, and `tests/self_check/config/test_every_slow_test_runs_in_a_ci_job.py`
holds the filter to what the slow tests read and run: every slow test file, conftest and
support module they import, and, since `beadloom-ujzb.24` (m6), every `src/beadloom` file the
beadloom steps of the build (`init`, `reindex`, `docs site`) enter, traced on every adopter
fixture in a fresh interpreter by `tests/support/slow_test_trace.py`. The hand list before it
missed 84 such files, `application/reindex` and the `init` command among them.

Scenarios: `tests/acceptance/application/site-generation/node_card_data.feature` (the card, the
source link per forge, no commit author and no credential in any generated file, an unreadable
remote), `layer_view_verdict.feature`, since BDL-080 `every_layer_rule_in_the_data_file.feature`
and `a_site_node_is_a_service_on_the_portal.feature`, and since slice 2 `portal_scaffold.feature`,
`pages_workflow.feature`, `pages_base_warning.feature`, `self_hosted_forge_links.feature`,
`project_links_on_the_portal.feature` and `project_text_is_not_a_vue_template.feature`, with
their steps under `tests/acceptance/steps/application/site-generation/`.

Unplaced, so bound to no node: `tests/test_site_generator.py`, `tests/test_site_dashboard.py`,
`tests/test_site_published_docs.py`, `tests/test_site_coverage_edges.py`,
`tests/test_site_viz_data_guards.py`, `tests/test_landscape_view.py`.

The viewer's browser tests are under `src/beadloom/site_scaffold/e2e/` (written into the portal's
`e2e/`) and bind to the theme's slices; see [the site's
page](../../../../services/vitepress-site.md#browser-tests).
