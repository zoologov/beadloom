# BDL-082 — axes and measured gaps

Measured on 2026-10-11 on `features/BDL-082` at `30605b71`, with `uv run beadloom` from this
tree, Node v22.9.0, Steiger 0.7.0 and `@feature-sliced/steiger-plugin` 0.8.0 installed by
`npm ci --ignore-scripts` from `src/beadloom/site_scaffold/package-lock.json` into a scratch
directory. Every probe project below is a scratch directory under the session scratchpad,
not part of this tree. Reference pages read the same day: `/docs/reference/layers`,
`/docs/reference/slices-segments`, `/docs/reference/public-api`,
`/docs/guides/migration/from-v2-0` on feature-sliced.design.

## Axes

### (a) `src/beadloom/graph/rules/slices.py`

> **Derived by:** `beadloom impact src/beadloom/graph/rules/slices.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 10 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | rule-engine | 2 — `src/beadloom/graph/rules/__init__.py:236` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site/architecture_card.py:117` | none | ? |  |
| branches | rule-engine | `_stem`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_node_sources`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_carriers`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_slice_folders`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_inside`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_located`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_slice_holding`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_is_the_index_of`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_has_index`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_public_api_finding`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_judge_import`: 2 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `evaluate_slice_public_api_rules`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_shape_findings`: 4 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `evaluate_slice_shape_rules`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `slice_rule_inert_reason`: 1 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | site-generation | `debt_inside`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_all`: 34 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_reasons_for_rule`: 14 branch(es), 14 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the `segments:` list `slice_shape` reads is parsed outside this module, in `src/beadloom/graph/rules/loader.py:1161` and defaulted at `src/beadloom/graph/rules/types.py:701`; no axis above names either site.

### (b) The same-layer crossing check — `same_layer_crossings` (`src/beadloom/graph/rules/layers.py:296`)

> **Derived by:** `beadloom impact same_layer_crossings` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | import-resolver | 1 — `src/beadloom/graph/import_resolver.py:1188` | none | ? |  |
| callers | rule-engine | 11 — `src/beadloom/graph/rules/evaluators.py:628` | none | ? |  |
| callers | site-generation | 6 — `src/beadloom/application/site/architecture_view.py:174` | none | ? |  |
| branches | rule-engine | `part_of_generations`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `part_of_ancestors`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `subtree_of`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `within_scope`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `own_layer_of`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `layer_membership`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `layer_of`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `tagged_containers`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `shares_tagged_ancestor`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `same_layer_crossings`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `can_fire_on`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `layer_population`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `inherited`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `total`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | site-generation | `token`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `rank`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `layer_rules_view`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `_derived_scope`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `placement`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `judges`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | import-resolver | `_part_of_ancestors`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_layer_rules`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_where`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_crossing_finding`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `same_layer_statements`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `reach_of`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `scoped_reach`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_layer_reasons`: 2 branch(es), 4 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `validate_rules`: 15 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_file_findings`: 3 branch(es), 3 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `holds_or_contains`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `covered_by`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |


### (c) `src/beadloom/onboarding/scanner/fsd_layout.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/fsd_layout.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 10 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| branches | agent-prime | `_is_architecture_folder`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_code_files`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_subfolders`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_layer_units`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `read_fsd_layout`: 5 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_routes_unit`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `fsd_tag`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `fsd_nodes`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `claimed`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `bootstrap_project`: 18 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | agent-prime | `_source_roots`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: where the FSD root is found — `fsd_root` and `FSD_LAYERS` in `src/beadloom/onboarding/presets.py:129` and `:170`, owned by node `onboarding` — is imported by this module and named by no axis above; the monorepo probe (gap 8) turns on it.

### (d) `src/beadloom/onboarding/scanner/rules_gen.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/rules_gen.py` over `src/beadloom`
> **Seed:** `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 1 name-defined-more-than-once, 5 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 3 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 1 — `src/beadloom/services/commands/index_ops.py:247` | none | ? |  |
| co-writers | doc-generator | 1 — `src/beadloom/onboarding/doc_generator.py:658` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| callers | agent-prime | 3 — `src/beadloom/onboarding/scanner/agents_md.py:215` | none | ? |  |
| branches | agent-prime | `generate_rules`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | agent-prime | `fsd_rules_text`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | agent-prime | `generate_fsd_rules`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | agent-prime | `_detect_rule_type`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | agent-prime | `_read_rules_data`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | agent-prime | `_build_rules_section`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `bootstrap_project`: 3 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `prime_context`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |

Not derivable: the five FSD overlays that restate these rules in prose — `src/beadloom/onboarding/templates/roles/architecture/fsd/{dev,explore,review,tech-writer,test}.md.txt`, owned by node `onboarding` and read as text through `src/beadloom/onboarding/composer.py:261` — are reached by no call, so every `Owns unread` cell above reads `none` and no row names them.

### (e) `src/beadloom/onboarding/scanner/steiger_script.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/steiger_script.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| callers | cli-commands | 3 — `src/beadloom/services/commands/setup.py:1545` | none | ? |  |
| branches | agent-prime | `_command`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_declared_packages`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_running_steiger`: 1 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_indent_of`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `_write_back`: 1 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `ensure_steiger_script`: 5 branch(es), 6 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `sentence`: 1 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | agent-prime | `bootstrap_project`: 18 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | agent-prime | `interactive_init`: 26 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_echo_unread_swift`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_echo_import_aliases`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_echo_steiger_script`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the scaffold's `src/beadloom/site_scaffold/steiger.config.js` and `src/beadloom/site_scaffold/package.json:26,29` (the pinned Steiger pair), owned by node `vitepress-site`, are not Python and are reached by no axis above.

### Nodes across the five sections

Seven distinct nodes: `rule-engine`, `import-resolver`, `graph-loader` (part_of `graph`);
`agent-prime`, `doc-generator` (part_of `onboarding`); `site-generation` (part_of
`application`); `cli-commands` (part_of `cli`). The two owners named only in `Not derivable:`
lines are `onboarding` (domain) and `vitepress-site` (service). `beadloom lint` on this tree
reported no `domain-size-limit` finding on any of these nodes (71 lines, measured).

## The measured gaps

### 1. `@x` cross-imports

**Spec.** `/docs/reference/layers` (Entity relationships): `entities/artist/model/artist.ts`
does `import type { Song } from "entities/song/@x/artist"`, and `entities/song/@x/artist.ts`
re-exports from `../model/song.ts`. `/docs/reference/public-api` (Public API for cross-imports):
"entity A can declare a separate public API just for entity B", with a note to use it only on
the Entities layer. `/docs/guides/migration/from-v2-0`: "Another addition … is the
standardization of cross-imports between entities with the @x-notation."

**Probe** `p1-x`: `src/{app,pages,entities,shared}`, `entities/song/{index.ts,model/song.ts,
@x/artist.ts}`, `entities/artist/{index.ts,model/artist.ts,model/rel.ts,ui/card.ts}`, three
import forms of the one `@x` file: the spec's bare `"entities/song/@x/artist"` (tsconfig
`baseUrl: ./src`), the alias `"@/entities/song/@x/artist"`, the relative `"../../song/@x/artist"`.

`beadloom init --yes` exited 1 with:

```
  fsd-layers: entities-artist
  fsd-public-api: src/entities/artist/model/artist.ts:1
  fsd-public-api: src/entities/artist/model/rel.ts:1
  fsd-public-api: src/entities/artist/ui/card.ts:1
`beadloom ci` will fail its lint step: 4 error(s), 4 warning(s), fsd-layers judged 4 of 4 live depends_on edge(s)
```

`beadloom lint --strict` exited 1. The FSD findings (`--format json`):

| Rule | Severity | Where | Message (abridged) |
|---|---|---|---|
| `fsd-layers` | error | edge `entities-artist → entities-song` (no file, no line) | Same-layer crossing … no container that declares a layer holds both |
| `fsd-public-api` | error | `src/entities/artist/model/artist.ts:1` | imports `'entities/song/@x/artist'`, which reaches past the public API of slice `entities-song` … into `src/entities/song/@x/artist.ts` |
| `fsd-public-api` | error | `src/entities/artist/model/rel.ts:1` | same, specifier `'../../song/@x/artist'` |
| `fsd-public-api` | error | `src/entities/artist/ui/card.ts:1` | same, specifier `'@/entities/song/@x/artist'` |
| `fsd-slice-shape` | warn | slice `entities-song` | holds the folder `'@x/'` at its top, which is not one of its segments |

Four false errors and one false warning on a project that follows the spec's own example. All
three import forms resolved, so the findings are not a resolution artefact.

**Where.** `src/beadloom/graph/rules/slices.py:174-175` (`_judge_import`): only a file for which
`_is_the_index_of` (`:122-124`) holds passes, so `@x/<slice>.ts` is "past the public API".
`slices.py:228` (`_shape_findings`): `@x` is not in `segments`. `src/beadloom/graph/rules/layers.py:296-317`
(`same_layer_crossings`): judges node pairs `(src_ref_id, dst_ref_id)`, so the edge carries no
file or specifier and cannot tell an `@x` import from any other; the call is
`src/beadloom/graph/rules/layer_crossings.py:121` (`same_layer_statements`). The only way to
silence the edge today is a layer exemption with an exit condition
(`src/beadloom/graph/rules/layer_exemptions.py`), which reads as a debt, not a sanctioned
pattern. The comment `init` writes says the opposite of Steiger:
`src/beadloom/onboarding/scanner/rules_gen.py:118-120` ("Cross imports inside one layer are
forbidden by the rule, as FSD prescribes … (Steiger: forbidden-imports)").

**Steiger on the same tree** (`npm run lint:fsd`, recommended set of 0.8.0): 4 errors, none on
the `@x` imports — `entities/artist` and `entities/song` `fsd/insignificant-slice`,
`src/pages/home/ui/home.ts:2:22` `fsd/no-public-api-sidestep` (into `@/shared/api/client`),
`src/shared/api` `fsd/public-api`. The exemption is in the plugin: `forbidden-imports`
skips a dependency when `isCrossImportPublicApi(...)` holds
(`node_modules/@feature-sliced/steiger-plugin/dist/index.js:549`), and
`@feature-sliced/filesystem` 3.1.1 defines it as `<layer>/<inSlice>/@x/<forSlice>.ts` or
`<layer>/<inSlice>/@x/<forSlice>/index.*` (`dist/index.js:128-138`). It is not restricted to
the Entities layer. Steiger also counted no reference to `entities/song` through `@x`
("This slice has no references").

### 2. Slice groups

**Spec.** `/docs/reference/slices-segments` (Slice groups): "Closely related slices can be
structurally grouped in a folder, but they should exercise the same isolation rules as other
slices — there should be no code sharing in that folder."

**Probe** `p2-groups`: `features/auth/login/{index.ts,ui/form.ts}`,
`features/auth/register/{index.ts,ui/form.ts}`, no `features/auth/index.ts`;
`register/ui/form.ts:1` imports `@/features/auth/login` (code sharing inside the group);
`pages/home/ui/home.ts:1-2` imports `@/features/auth/login` and `@/features/auth/register`.

`init --yes` wrote ONE node for the group: `features-auth`, `source: src/features/auth/`,
tags `[fsd-features]`, summary "auth — 2 fns". No node for `login` or `register`. It exited 1:

| Rule | Severity | Where | Message (abridged) |
|---|---|---|---|
| `fsd-public-api` | error | `src/pages/home/ui/home.ts:1` | imports `'@/features/auth/login'` into slice `features-auth`, which has no index |
| `fsd-public-api` | error | `src/pages/home/ui/home.ts:2` | same, `'@/features/auth/register'` |
| `fsd-slice-shape` | warn | slice `features-auth` | holds the folder `'login/'` at its top |
| `fsd-slice-shape` | warn | slice `features-auth` | holds the folder `'register/'` at its top |
| `fsd-layers` | — | — | no finding: `register → login` is inside one node, so it is no edge |

Two false errors and two false warnings, and the one real violation the spec names (sharing
inside the group) is invisible. Steiger on the same tree reported it:
`src/features/auth/register/ui/form.ts:1:28 ✘ Forbidden cross-import from slice "auth/login"`
(`fsd/forbidden-imports`), and read `auth/login` and `auth/register` as two slices.

**Where.** `src/beadloom/onboarding/scanner/fsd_layout.py:160-165` (`_layer_units`): every
direct subfolder of a sliced layer becomes one `SLICE` unit named `<layer>-<folder>`;
`:137-147` (`_code_files`) collects every code file below it with `rglob`, so the group's
slices are flattened into it. The module docstring states the limit at `fsd_layout.py:35-36`.
`slices.py:165-173` (`_judge_import`) is the "no index" finding. Steiger's group rule:
`@feature-sliced/filesystem` `getSlices`/`isSlice` (`dist/index.js:47-61`, `:139-143`) — a
folder is a slice when a child is named `ui`, `api`, `lib`, `model` or `config`; otherwise
it is a group and is descended.

### 3. Pages-first

**Spec.** `/docs/guides/migration/from-v2-0`: "The main change in v2.1 is the new mental
model for decomposing an interface — pages first … you keep most of the UI and logic in each
individual page". `/docs/reference/layers` (Pages): "There's no limit to how much code you can
place in a page slice as long as your team still finds it easy to navigate."

**Where the limit is written.** `src/beadloom/onboarding/scanner/rules_gen.py:90-97`
(`FSD_COHESION_LIMITS`: `pages: 60`, `widgets: 80`, others 60), rendered one `check` rule per
layer by `rules_gen.py:166-173` and `:194-197`. It is per layer: `fsd-cohesion-pages` has
`for: { kind: component, tag: fsd-pages }`, `max_symbols: 60`, severity `warn`. The calibration
comment (`rules_gen.py:83-89`, `:158-164`) is Beadloom's own portal's largest widget, 65
symbols.

**Fixtures after `init --yes`** (symbols per node from `code_symbols`, by source prefix):

| Fixture | `pages` slice | Symbols | Limit | Fires |
|---|---|---|---|---|
| `tests/fixtures/site/vue-fsd` | `pages-catalog` | 1 | 60 | no |
| `tests/fixtures/site/vue-fsd` | `pages-checkout` | 1 | 60 | no |
| `tests/fixtures/site/rn-fsd` | `pages-home` | 1 | 60 | no |
| `tests/fixtures/site/rn-fsd` | `pages-trail` | 1 | 60 | no |

Both fixtures are total 24 and 26 symbols, so neither exercises the limit. Their lint
findings are unrelated to cohesion (vue-fsd: `fsd-layers` `features-apply-coupon →
features-add-to-cart`, `fsd-public-api` `src/widgets/product-grid/ui/ProductGrid.vue:3`;
rn-fsd: `fsd-slice-shape` on `features-start-hike`).

**Probe** `p3-pagesfirst`: `pages/feed` with 90 functions over `ui/`, `api/`, `model/`,
`pages/profile` with 45, `shared` with 7, no `widgets`, `features` or `entities`. `lint`:

```
fsd-cohesion-pages | pages-feed | Node 'pages-feed' has 90 symbols (max 60): rule 'fsd-cohesion-pages'
fsd-cohesion-entities | Rule 'fsd-cohesion-entities' cannot fire: its `for` tag 'fsd-entities' is carried by no node.
fsd-cohesion-features | … 'fsd-features' is carried by no node.
fsd-cohesion-widgets  | … 'fsd-widgets' is carried by no node.
fsd-layers | this rule declares 6 layer(s) and 3 of them hold a node …
```

A project doing what v2.1 recommends gets a split signal on its main page and three
cannot-fire statements. The overlay asks for the split
(`src/beadloom/onboarding/templates/roles/architecture/fsd/dev.md.txt:25`: "A slice past it
is split by responsibility").

### 4. Custom segments

**Spec.** `/docs/reference/slices-segments` (Segments): "You can also create custom segments
… Make sure that the name of these segments describes the purpose of the content, not its
essence. For example, components, hooks, and types are bad segment names".

**Probe** `p45-segments`: `features/x/{ui,analytics,components,hooks}/` plus `index.ts`.
`lint` (rules as `init` wrote them):

```
fsd-slice-shape | Slice 'features-x' holds the folder 'analytics/' at its top, which is not one of its segments (ui, model, lib, api, config)
fsd-slice-shape | Slice 'features-x' holds the folder 'components/' at its top, …
fsd-slice-shape | Slice 'features-x' holds the folder 'hooks/' at its top, …
```

The purposeful `analytics/` and the discouraged `components/`, `hooks/` get one identical
warning. The list is editable: `rules.yml` line 58 in the probe,
`segments: [ui, model, lib, api, config]` → `[…, analytics]`, then `lint` reported 2
`slice_shape` findings instead of 3. Parsed at `src/beadloom/graph/rules/loader.py:1161-1165`,
defaulted at `src/beadloom/graph/rules/types.py:701`, written at
`src/beadloom/onboarding/scanner/rules_gen.py:155`; the check is an allow-list at
`src/beadloom/graph/rules/slices.py:228`. Steiger on the same tree flagged
`src/features/x/components` and `src/features/x/hooks` (`fsd/segments-by-purpose`, a deny-list
`BAD_NAMES`, plugin `dist/index.js:1025-1096`, rule at `:1097`) and not `analytics`.

### 5. Shared's per-component index; `app`/`shared` custom segments

**Spec.** `/docs/reference/public-api` (Large bundles … in Shared): for `shared/ui` and
`shared/lib`, "have a separate index file for each component or library", imported as
`@/shared/ui/button`. `/docs/reference/slices-segments`: "Every slice (and segment on layers
that don't have slices) must contain a public API definition." `/docs/reference/layers`:
`shared` segments `api`, `ui`, `lib`, `config`, `routes`, `i18n`; `app` segments `routes`,
`store`, `styles`, `entrypoint`.

**Probe** `p45-segments`: `shared/ui/{button,text-field}/index.ts`, `shared/{i18n,routes}/index.ts`,
`app/{entrypoint,routes,store,styles}`; `pages/home/ui/home.ts` imports `@/shared/ui/button`
(line 1, per-component index), `@/shared/ui/text-field/text-field` (line 2, past it),
`@/shared/i18n` (line 3), `@/shared/routes/paths` (line 4, past the segment index).

Nodes `init` wrote: `shared` (container), `shared-i18n`, `shared-routes`, `shared-ui` (one
node; no node for `button` or `text-field`), `app` (container), `app-entrypoint`,
`app-routes`, `app-store`, `app-styles`, all tagged with their layer and `part_of` the
container. No Beadloom rule produced a finding on any `shared` or `app` import, either sidestep
included: `fsd-public-api` and `fsd-slice-shape` are written with
`tags: [fsd-pages, fsd-widgets, fsd-features, fsd-entities]` only
(`rules_gen.py:100` `_SLICED_LAYERS`, `:178`). The per-component layout is therefore neither
wrongly flagged nor read: `fsd_layout.py:167-178` makes one segment per folder of `shared`
and `app` and stops there.

Steiger on the same tree: `src/pages/home/ui/home.ts:2:28 ✘ Forbidden sidestep of public API
when importing from "@/shared/ui/text-field/text-field"`, `:4:27 ⚠ … "@/shared/routes/paths"`,
nothing on line 1 (the per-component index is accepted), and `src/app/store ✘ This segment's
name should describe the purpose of its contents` (`store` is in the plugin's `BAD_NAMES`,
`dist/index.js:1038`, while `/docs/reference/layers` lists `store` as a typical `app`
segment). In `p1-x` Steiger also reported `src/shared/api ✘ This segment is missing a public
API` (`fsd/public-api`), which Beadloom does not check.

### 6. The Steiger version

| Package | Scaffold pin | Latest on npm (2026-10-11) | Released |
|---|---|---|---|
| `steiger` | `0.7.0` (`src/beadloom/site_scaffold/package.json:29`) | `0.7.0` (`npm view steiger version`) | — |
| `@feature-sliced/steiger-plugin` | `0.8.0` (`package.json:26`) | `0.8.0` (`npm view … version`) | 2026-09-25 |

The scaffold is current. The fixture `tests/fixtures/site/vue-fsd/package.json` pins
`steiger 0.5.3` and plugin `0.5.1`. The sentence `init` prints installs unpinned
(`src/beadloom/onboarding/scanner/steiger_script.py:71-72`).

Plugin 0.8.0 (measured by importing `fsd.configs.recommended` from the installed package)
defines 21 rules and turns 17 on in `recommended`, all `error`:
`ambiguous-slice-names`, `excessive-slicing`, `forbidden-imports`, `inconsistent-naming`,
`insignificant-slice`, `no-layer-public-api`, `no-public-api-sidestep`,
`no-reserved-folder-names`, `no-segmentless-slices`, `no-segments-on-sliced-layers`,
`no-ui-in-app`, `public-api`, `repetitive-naming`, `segments-by-purpose`, `shared-lib-grouping`,
`typo-in-layer-name`, `no-processes`. Defined and off: `no-cross-imports`,
`no-higher-level-imports`, `import-locality`, `no-wildcard-exports`. The header `init` writes
names 5 of the 17 as "its `recommended` set" (`rules_gen.py:105-107`). The recommended set at
0.5.1 was not measured.

### 7. The overlays' best-practice text against the spec

Files: `src/beadloom/onboarding/templates/roles/architecture/fsd/{dev,explore,review,test,tech-writer}.md.txt`.

| Claim (file:line) | Spec (page) | Verdict |
|---|---|---|
| "No cross-imports between slices of the SAME layer — go through `shared`/`entities` or lift" (`dev.md.txt:10`) | `@x` is the sanctioned cross-import between entities (public-api, layers, migration) | contradicts: `@x` absent |
| "no cross-slice import within the same layer" (`review.md.txt:8`); "never reach across same-layer slices in a test (that import is illegal anyway)" (`test.md.txt:5`) | as above | contradicts: `@x` absent |
| "`processes` is deprecated since FSD 2.1 and carries no tag" (`dev.md.txt:10`) | layers: "Processes (deprecated)"; no page read states the version | deprecated: matches; "since 2.1": not stated on the pages read |
| Segments are `ui`, `model`, `api`, `lib`, `config` (`dev.md.txt:11`); "Segments stay within their role (`ui` / `model` / `api` / `lib` / `config`)" (`review.md.txt:10`) | custom segments allowed if named by purpose (slices-segments) | incomplete: custom segments absent |
| "A slice's top holds its segments and its `index` and nothing else" (`dev.md.txt:21`) | slices-segments: "Inside a slice, the code could be organized in any way that you want" so long as the public API holds | stricter than spec |
| Another slice is entered through its `index` only (`dev.md.txt:20`, `review.md.txt:9`) | public-api: `index` plus `@x/<slice>`, plus environment-specific public API files | incomplete |
| Steiger's `public-api` "reports a slice that has no `index`" (`dev.md.txt:20`, `review.md.txt:9`) | slices-segments: every slice AND every segment of `app`/`shared` needs a public API; Steiger reported `src/shared/api` | incomplete: segments omitted |
| "Inside your own slice, import relatively rather than through your own `index`" (`dev.md.txt:20`) | public-api (Circular imports): same slice → relative, full path | matches |
| A slice past `max_symbols` "is split by responsibility" (`dev.md.txt:25`); limit 60 for `pages` | pages-first; layers: "There's no limit to how much code you can place in a page slice" | contradicts for `pages` |
| "a feature one widget alone uses is still a feature … `insignificant-slice` … is weighed, not obeyed" (`dev.md.txt:26`) | migration v2.1 names `insignificant-slice` and `excessive-slicing` as "the most helpful rules"; layers: "not everything needs to be a feature" | diverges; reason stated for the portal at `src/beadloom/site_scaffold/steiger.config.js:8-15` |
| Slice groups | slices-segments: groups allowed, isolation kept | absent from all five overlays |
| Barrel pitfalls: no `export *` | public-api: "❌ BAD CODE … `export * from`" | absent; Steiger `no-wildcard-exports` is off in `recommended` |
| Barrel pitfalls: no index on segments of sliced layers | public-api: "Avoid having index files in segments on layers that have slices" | absent |
| Barrel pitfalls: per-component index in `shared/ui`, `shared/lib` | public-api (Large bundles … in Shared) | absent |
| A slice maps to one `component` node `part_of` the frontend (`dev.md.txt:15`, `explore.md.txt:5`) | — (graph mapping, not a spec claim) | not applicable; false for a slice group (gap 2) |
| "one doc per slice node … describing the slice's public API (its `index`)" (`tech-writer.md.txt:4`) | public-api | incomplete: `@x` absent |

### 8. Monorepo FSD (for the record)

**Probe** `p8-monorepo`: root `package.json` with `workspaces: ["packages/*"]`,
`packages/app/src/{app,pages,entities,shared}`. `init --yes`:

```
  Graph: 3 nodes, 2 edges (preset: monorepo)
```

Nodes `probe-mono`, `app` (`packages/app/`), `app-src` (`packages/app/src/`), all `service`;
no FSD node, no tag, and no `rules.yml` written. `fsd_root` looks only at `src/` and the
project root (`src/beadloom/onboarding/presets.py:137`, `:170-181`); the docstring states it
(`fsd_layout.py:35-36`). The spec's public-api page (Worse performance … on large projects)
describes "a monorepo setup where each package is a separate FSD root".

## Open questions for the owner

1. **`@x` in the layer rule.** Making the `entities-artist → entities-song` edge legal needs
   the import's target file, which the edge does not carry (`layers.py:296-317`). Either the
   layer rule reads `code_imports` for same-layer edges (accurate, but the layer rule stops
   being a pure graph rule), or `slice_public_api` owns `@x` and the layer rule accepts an edge
   whose every import lands on `@x/<src-slice>` via a derived edge attribute (keeps the rule
   graph-level, adds a new edge fact the reindex must write).
2. **`@x` outside Entities.** The spec says "only use this notation on the Entities layer";
   Steiger accepts it on every sliced layer (`isCrossImportPublicApi` has no layer check).
   Accepting it only on `entities` matches the spec's text and disagrees with Steiger on
   `features/a/@x/b`; accepting it everywhere agrees with Steiger and drops the spec's note.
3. **How a slice group is recognised.** Steiger's test (a folder is a slice when it holds a
   standard segment) needs no configuration, but reads a slice whose only folders are custom
   segments as a group. Testing for an `index` at the folder agrees with `slice_public_api`
   and misreads a group that carries its own `index`. The ref-id of a grouped slice
   (`features-auth-login`) is also undecided.
4. **The `pages` limit.** Keep 60 with a written reason, raise it, or write no cohesion check
   for `pages`. Keeping it signals a split on a v2.1 project's main page (measured: 90
   symbols fires); dropping it leaves `pages` the one layer with no size signal.
5. **`insignificant-slice`.** The portal turns it off for graph-parallelism
   (`steiger.config.js:8-15`) and the overlay says "weighed, not obeyed"; v2.1 names it as the
   most helpful rule. Whether the adopter-facing overlay carries Beadloom's reason or the spec's
   is a positioning decision.
6. **Custom segments: allow-list or deny-list.** `slice_shape` allows five names and flags the
   rest; Steiger allows any name and flags `BAD_NAMES`. An allow-list catches a misplaced dump
   folder with an unusual name; a deny-list stops flagging purposeful segments like
   `analytics`.
7. **Public API of `shared` and `app` segments.** The spec requires one per segment, and
   per-component indexes in `shared/ui`/`shared/lib`. Extending `slice_public_api` to the
   segment tags would make the `p45` sidesteps findings, and needs a decision on whether a
   nested `shared/ui/button/index` is a public API (Steiger: yes) or a node of its own.
8. **Monorepo FSD** (gap 8): in BDL-082 or a later item.
