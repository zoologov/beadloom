# RFC: BDL-082 — FSD by the specification 2.1

> **Status:** Approved
> **Created:** 2026-10-11

---

## Summary

Beadloom's FSD support is brought to feature-sliced.design's reference (2.1): the `@x`
cross-import convention, slice groups, pages-first, custom segments by purpose, the public API
of the unsliced layers, and overlays that say the specification. Two slices, one PR each: S1 the
rules and the reindex's edge fact; S2 `init`'s layout reader and written rules, the overlays, the
fixtures. The measurement is `axes.md`; the owner's eight rulings are in PRD.md.

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
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: the target reaches no declared effect sink |
| callers | rule-engine | 2 — `src/beadloom/graph/rules/__init__.py:236` | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| callers | site-generation | 1 — `src/beadloom/application/site/architecture_card.py:117` | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | rule-engine | `_stem`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_node_sources`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_carriers`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_slice_folders`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_inside`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_located`: 3 branch(es), 3 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_slice_holding`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_is_the_index_of`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_has_index`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_public_api_finding`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_judge_import`: 2 branch(es), 3 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `evaluate_slice_public_api_rules`: 2 branch(es), 2 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_shape_findings`: 4 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `evaluate_slice_shape_rules`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `slice_rule_inert_reason`: 1 branch(es), 3 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | site-generation | `debt_inside`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | rule-engine | `evaluate_all`: 34 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_reasons_for_rule`: 14 branch(es), 14 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |

Not derivable: the `segments:` list `slice_shape` reads is parsed outside this module, in `src/beadloom/graph/rules/loader.py:1161` and defaulted at `src/beadloom/graph/rules/types.py:701`; no axis above names either site.

### (b) The same-layer crossing check — `same_layer_crossings` (`src/beadloom/graph/rules/layers.py:296`)

> **Derived by:** `beadloom impact same_layer_crossings` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: the target reaches no declared effect sink |
| callers | import-resolver | 1 — `src/beadloom/graph/import_resolver.py:1188` | none | yes | the reindex writes the derived `@x` edge fact (D1) |
| callers | rule-engine | 11 — `src/beadloom/graph/rules/evaluators.py:628` | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| callers | site-generation | 6 — `src/beadloom/application/site/architecture_view.py:174` | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | rule-engine | `part_of_generations`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `part_of_ancestors`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `subtree_of`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `within_scope`: 2 branch(es), 2 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `own_layer_of`: 1 branch(es), 2 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `layer_membership`: 3 branch(es), 3 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `layer_of`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `tagged_containers`: 2 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `shares_tagged_ancestor`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `same_layer_crossings`: 2 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `can_fire_on`: 1 branch(es), 2 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `layer_population`: 1 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `inherited`: 0 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `total`: 0 branch(es), 1 exit form(s), over every call | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | site-generation | `token`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | site-generation | `rank`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | site-generation | `layer_rules_view`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | site-generation | `_derived_scope`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | site-generation | `placement`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | site-generation | `judges`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | import-resolver | `_part_of_ancestors`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the reindex writes the derived `@x` edge fact (D1) |
| branches | rule-engine | `evaluate_layer_rules`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_where`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_crossing_finding`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `same_layer_statements`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `reach_of`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `scoped_reach`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_layer_reasons`: 2 branch(es), 4 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `validate_rules`: 15 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `_file_findings`: 3 branch(es), 3 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `holds_or_contains`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |
| branches | rule-engine | `covered_by`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | the slice rules and the same-layer crossing check change (D1, D2, D4, D5) |


### (c) `src/beadloom/onboarding/scanner/fsd_layout.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/fsd_layout.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 10 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: the target reaches no declared effect sink |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_is_architecture_folder`: 1 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_code_files`: 1 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_subfolders`: 1 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_layer_units`: 3 branch(es), 3 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `read_fsd_layout`: 5 branch(es), 3 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_routes_unit`: 1 branch(es), 2 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `fsd_tag`: 0 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `fsd_nodes`: 1 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `claimed`: 3 branch(es), 3 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `bootstrap_project`: 18 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_source_roots`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |

Not derivable: where the FSD root is found — `fsd_root` and `FSD_LAYERS` in `src/beadloom/onboarding/presets.py:129` and `:170`, owned by node `onboarding` — is imported by this module and named by no axis above; the monorepo probe (gap 8) turns on it.

### (d) `src/beadloom/onboarding/scanner/rules_gen.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/rules_gen.py` over `src/beadloom`
> **Seed:** `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 1 name-defined-more-than-once, 5 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 3 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| co-writers | cli-commands | 1 — `src/beadloom/services/commands/index_ops.py:247` | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| co-writers | doc-generator | 1 — `src/beadloom/onboarding/doc_generator.py:658` | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | yes | edge attributes the fact is stored on (D1); read only if the schema needs a column |
| callers | agent-prime | 3 — `src/beadloom/onboarding/scanner/agents_md.py:215` | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `generate_rules`: 1 branch(es), 2 exit form(s) | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `fsd_rules_text`: 0 branch(es), 1 exit form(s) | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `generate_fsd_rules`: 0 branch(es), 1 exit form(s) | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_detect_rule_type`: 0 branch(es), 2 exit form(s) | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_read_rules_data`: 0 branch(es), 2 exit form(s) | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_build_rules_section`: 0 branch(es), 2 exit form(s), from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `bootstrap_project`: 3 branch(es), 1 exit form(s), from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `prime_context`: 0 branch(es), 2 exit form(s), from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |

Not derivable: the five FSD overlays that restate these rules in prose — `src/beadloom/onboarding/templates/roles/architecture/fsd/{dev,explore,review,tech-writer,test}.md.txt`, owned by node `onboarding` and read as text through `src/beadloom/onboarding/composer.py:261` — are reached by no call, so every `Owns unread` cell above reads `none` and no row names them.

### (e) `src/beadloom/onboarding/scanner/steiger_script.py`

> **Derived by:** `beadloom impact src/beadloom/onboarding/scanner/steiger_script.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: the target reaches no declared effect sink |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| callers | cli-commands | 3 — `src/beadloom/services/commands/setup.py:1545` | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | agent-prime | `_command`: 0 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_declared_packages`: 2 branch(es), 1 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_running_steiger`: 1 branch(es), 3 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_indent_of`: 1 branch(es), 2 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `_write_back`: 1 branch(es), 0 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `ensure_steiger_script`: 5 branch(es), 6 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `sentence`: 1 branch(es), 4 exit form(s), over every call | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `bootstrap_project`: 18 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | agent-prime | `interactive_init`: 26 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | `fsd_layout.py`, `rules_gen.py`, `steiger_script.py` change (D2, D3, D4, D6) |
| branches | cli-commands | `_echo_unread_swift`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | cli-commands | `_echo_import_aliases`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |
| branches | cli-commands | `_echo_steiger_script`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | blast radius: a reader of the rules or the layout, not edited by this change |

Not derivable: the scaffold's `src/beadloom/site_scaffold/steiger.config.js` and `src/beadloom/site_scaffold/package.json:26,29` (the pinned Steiger pair), owned by node `vitepress-site`, are not Python and are reached by no axis above.

### (f) The viewer on the 21-node fixtures — `src/beadloom/site_scaffold/.vitepress/theme/features/overview-map/model/overviewPlan.js` (S2c, added 2026-10-13)

> **Derived by:** `beadloom impact src/beadloom/site_scaffold/.vitepress/theme/features/overview-map/model/overviewPlan.js` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files, 1 unreadable-target

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — this derivation reads Python source and could not read the target, so nothing that file defines was read and no caller or writer of it was found | — | ? | the derivation cannot reach JavaScript (`beadloom-j1ke`); ruled by the owner below |
| callers | — | unresolved — the same | — | ? | the same |

Ruled in by the owner's two rulings on `beadloom-us5r.1` (2026-10-11: every title inside its box, the legend's one sample per colour of a mixed line) rather than by a derived row, because `impact` reads Python only: `site-overview-map`, `site-graph-viewer`, `site-shared-grid-routing`, `site-shared-map-levels`, `site-shared-geometry`, `site-graph-edges`, `site-edge-pills` (all part_of `vitepress-site`), and `vitepress-site` for the shipped browser specs under `e2e/`. S2c was not in the approved PLAN; it was opened on S2b's measurement (nine browser cases red on the 21-node fixtures) and its edge to S2b removed by the owner on 2026-10-11. The pre-commit scope check still reports every S2c path `outside-the-declared-axes`: it reads this section's tables as zero rows (BDL-UX #316), so the advisory stays until #316 closes and is not a finding against S2c.

### Nodes across the six sections

Seven distinct nodes: `rule-engine`, `import-resolver`, `graph-loader` (part_of `graph`);
`agent-prime`, `doc-generator` (part_of `onboarding`); `site-generation` (part_of
`application`); `cli-commands` (part_of `cli`). The two owners named only in `Not derivable:`
lines are `onboarding` (domain) and `vitepress-site` (service). `beadloom lint` on this tree
reported no `domain-size-limit` finding on any of these nodes (71 lines, measured).

Ruled in by the goals rather than by a derived row: `onboarding` (the five fsd overlays under
`onboarding/templates/roles/architecture/fsd/*`, in no row because templates are not Python)
and `vitepress-site` (`steiger.config.js` and the scaffold's `package.json`, read only; the
portal's own Steiger exception stays). `doc-generator` and `cli-commands` surface as readers and are not edited. Widened by S1a
(2026-10-11): `federation` (`export.py`) and `site-generation` (`architecture_view.py`) carry
the edge fact `via: "@x"` where edge attributes already travel — both ruled in for that one
attribute.

## Decisions

### D1 — `@x` as a derived edge fact (S1; rulings 1, 2)

The reindex, when it derives a `depends_on` edge between two slices of one sliced layer, records
on the edge whether every import of it lands on `<target>/@x/<importing slice's folder name>`
(a new edge attribute, additive, in the index and in `export` / the data file as `via: "@x"` —
name it in the public-API guide as a value added to the edge vocabulary). `same_layer_crossings`
(`graph/rules/layers.py:296`) accepts such an edge when both ends carry the entities layer's
tag, and reports it with the specification's wording otherwise ("`@x` is for the Entities
layer only"). `slice_public_api` (`graph/rules/slices.py`) reads `@x/<B>` as a second public API
of A open to B alone: an import of `A/@x/B` from a slice other than B is a finding; `slice_shape`
knows `@x` as a folder of a slice. Cases: the specification's example clean; a third slice
importing `A/@x/B` a finding; `features/a/@x/b` a finding; Steiger's verdict on the same trees
stated beside ours.

### D2 — slice groups (S2, with S1's rules unchanged; ruling 3)

`fsd_layout.py`: a folder in a sliced layer is a slice when it holds a standard segment
(`ui`, `model`, `api`, `lib`, `config`) or an `index`; a folder that holds neither and whose
children are slices is a group — one node per inner slice, ref id `<layer>-<group>-<slice>`,
source the inner folder, the layer's tag; the group has no node; a code file at the group's
top is a finding of `slice_shape` ("a group shares no code"). `rules_gen.py` unchanged in
shape. Cases: `features/auth/` holding `login` and `register` → two nodes; `register → login`
a `fsd-layers` error; no false "no index".

*Refined by the owner on 2026-10-13 (option (c), after S2R):* a folder holding code at its top is a group only when a child holds a standard segment, and a slice when its children carry only an index; a code-free folder is a group when its children are slices, at any depth. Both measured probes (a pre-migration slice with an index-bearing component folder; the specification's group with a shared file) hold.

### D3 — pages-first (S2; ruling 4)

`rules_gen.py` writes no `fsd-cohesion-pages`; the other five cohesion checks stay; the
overlay states pages-first as the specification does (start in `pages`, extract on real reuse,
duplication allowed). This repository's `rules.yml` keeps its own checks (the portal is not a
pages-first app). An adopter's existing `rules.yml` is not edited by an upgrade.

### D4 — custom segments by purpose (S1 the rule, S2 the written rule; ruling 6)

`slice_shape` gains `discouraged:` (default: the installed Steiger plugin's `BAD_NAMES` — 69
names in plugin 0.8.0, among them `components`, `hooks`, `types`, `utils`, `helpers`, `store`,
`services`, `constants`, `composables`, `actions`, `reducers`; the code quotes the whole list,
verified by program in S1) and keeps `segments:` as the known-good set; a folder in neither list is fine; a folder in
`discouraged:` is a finding with the specification's reason ("name by purpose, not essence").
`init` writes both lists with a comment.

### D5 — the public API of `shared` and `app` (S1; ruling 7)

`slice_public_api` accepts the unsliced layers' segment tags: a segment of `shared` or `app` is
entered through its index; in `shared/ui` and `shared/lib`, a per-component index
(`shared/ui/button/index`) is a public API entry, not a node. `init` tags the rule with every
layer. Cases: the two measured sidesteps into `shared` are findings; `shared/ui/button` is
clean; `app/store` imported from a page through its index is clean.

### D6 — the overlays and the written rules (S2; rulings 5, 6)

The five fsd overlays restated: `@x` on entities, groups, pages-first, custom segments,
the three barrel pitfalls (no `export *`, no index on a segment, per-component index in
`shared`), the public API of unsliced layers; `insignificant-slice` on for adopters, with this
portal's switch-off named as a reasoned exception. The `init`-written header lists the 17
recommended Steiger rules, one line each, from the plugin's own list. `setup-agentic-flow`
recomposes; this repository composes ddd, so no composed file changes here.

## Public API (MINOR)

- `rules.yml` vocabulary: `slice_shape` gains `discouraged:`; `fsd-cohesion-pages` is no
  longer written by `init` (existing files untouched).
- `export` / the data file: edges gain `via` with the value `@x` (additive).
- Exit codes move only on inputs 9.0.0 read wrongly (`@x`, groups): false findings disappear
  and real ones appear on spec-following projects; the RFC's cases measure both directions and
  the CHANGELOG names them under Changed with the measurement.

## Slices

- **S1** rules + the edge fact (D1, D4, D5): dev, test, review, docs, PR.
- **S2** `init` + overlays + fixtures (D2, D3, D6; the two FSD fixtures gain a group and an
  `@x` pair; the eight adopter portals green): dev, test, review, docs, PR.
