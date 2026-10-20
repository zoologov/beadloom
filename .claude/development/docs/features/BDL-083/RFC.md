# RFC: BDL-083 — Debt to zero

> **Status:** Approved
> **Created:** 2026-10-18

---

## Summary

Seven slices, one PR each, in the order the PRD's ruling 1 fixed: S1 the gates that lie, S2 the
monorepo on GitLab, S3 the re-measurement of every open entry, S4 the false-stale family, S5 the
original debt A–D, S6 the tooling baseline E–I, S7 the remaining beads and the recurrence that
keeps the count at zero. S1 and S2 are designed here to the bead; S3 produces the bead lists of
S4–S7, so those slices are designed when S3 closes, each as a PLAN section approved on its own.
The adopter's layout is rebuilt as a fixture in S1 and is the measurement of S2. The version is
MAJOR by three measured moves (D8).

## Axes

Derived, never authored. Eight targets, the modules of S1 and S2, derived by the Explore role on
2026-10-18 at `0f1cb9a3` and re-rendered verbatim by `beadloom impact <target> --section`; the
undecided originals are in `axes.md` beside this document. Every row is ruled below by the node's
role in the change, not by the axis it surfaced under. The co-writer rows of every table are the
same seven nodes reached through the YAML sinks `write_yaml_atomic` and `each_graph_file`; none
of the eight changes writes YAML, so they are ruled `no` once per table with that reason. Two
targets (`liveness.py`, `rooms.py`) reach no declared sink and their co-writer row is unresolved
by derivation. Nothing in `src/beadloom/tui/styles/*.tcss` was read (the TUI's four unread files);
they style a widget and carry no rule text, which is the reason the TUI rows are `no`.

Kept nodes, by slice: S1 — `cli-commands` (the hook templates, `ci`, `issue-number check`,
`scope-check`), `rule-engine` (liveness), `gate-ownership`, `declared-scope`, `ci-gate`,
`review-brief` (#344 by the shared base); S2 — `verdict-room`, `wave-plan`, `cli-commands`
(`rooms`, `clean-room`), `gate-coverage`, `ci-gate` (`_step_config_check`). Thirteen nodes over
the two slices: the full flow, as the PRD took it.

The targets of S3–S7 are derived when each slice's PLAN section is written; their axes are
appended to this section then, under the same rule.

### `src/beadloom/services/commands/docsync.py`


> **Derived by:** `beadloom impact src/beadloom/services/commands/docsync.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 50 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | application | 1 — `src/beadloom/application/gate_document_pairs.py:147` | none | no | `gate_document_pairs` calls the README-pair summary; the hook text is not on that path |
| branches | cli-commands | `sync_check`: 4 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_pair_label`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_unverified_why`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_stale_remedies`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_build_sync_report`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_hook_type_check`: 0 branch(es), 1 exit form(s) | none | yes | the composed hook templates live here: the pre-push fail-safe (#326), `beadloom lint` for staged node paths (#326), the ruff leg's stderr and configuration (#327) |
| branches | cli-commands | `install_hooks`: 0 branch(es), 2 exit form(s) | none | yes | the composed hook templates live here: the pre-push fail-safe (#326), `beadloom lint` for staged node paths (#326), the ruff leg's stderr and configuration (#327) |
| branches | cli-commands | `pre_commit_hook_body`: 0 branch(es), 1 exit form(s) | none | yes | the composed hook templates live here: the pre-push fail-safe (#326), `beadloom lint` for staged node paths (#326), the ruff leg's stderr and configuration (#327) |
| branches | cli-commands | `_write_hook`: 0 branch(es), 0 exit form(s) | none | yes | the composed hook templates live here: the pre-push fail-safe (#326), `beadloom lint` for staged node paths (#326), the ruff leg's stderr and configuration (#327) |
| branches | cli-commands | `_remove_hooks`: 0 branch(es), 0 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_bd_statuses_from_list`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_bd_epic_prefixes`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_query_bd_beads`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_query_bd_statuses`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_jsonl_is_tracked`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_export_jsonl`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_restage_within_this_commit`: 1 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_repo_relative`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `active_sync`: 3 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_has_active_table`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_active_sync_check`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_rebased`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_emit_active_sync`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_echo_unresolved`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_echo_named_by_an_unresolved_row`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_echo_unlisted`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_echo_staging`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_grounded_pairs`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_report_attestation`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_mark_synced_noninteractive`: 4 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_report_left_stale`: 1 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_why_left`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_resolve_scope`: 1 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_named_pairs`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_reject_unknown`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `sync_update`: 4 branch(es), 8 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `rebase`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | application | `_document_pair_summary`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |


### `src/beadloom/graph/rules/liveness.py`


> **Derived by:** `beadloom impact src/beadloom/graph/rules/liveness.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 1 node-owns-unread-files, 36 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: no declared sink is reached, so there is no commit point to co-write; the change adds none |
| callers | graph | 1 — `src/beadloom/graph/linter.py:233` | none | no | renders or forwards the finding text; the sentence changes, the channel does not. The TUI's 4 unread stylesheet files style a widget and carry no rule text |
| callers | rule-engine | 1 — `src/beadloom/graph/rules/__init__.py:248` | none | no | `__init__` registers the evaluator; the registration does not change |
| callers | site-generation | 2 — `src/beadloom/application/site/generate.py:130` | none | no | renders or forwards the finding text; the sentence changes, the channel does not. The TUI's 4 unread stylesheet files style a widget and carry no rule text |
| callers | tui | 16 — `src/beadloom/tui/app.py:69` | 4 — `src/beadloom/tui/styles/app.tcss` | no | renders or forwards the finding text; the sentence changes, the channel does not. The TUI's 4 unread stylesheet files style a widget and carry no rule text |
| branches | rule-engine | `_matcher_reason`: 2 branch(es), 6 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `_reasons_for_matchers`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_deny_reasons`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_require_reasons`: 2 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_cycle_reasons`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_forbid_edge_reasons`: 2 branch(es), 1 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `_layer_reasons`: 2 branch(es), 4 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_cardinality_reasons`: 2 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_unregistered_reasons`: 2 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_module_coverage_reasons`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_scenario_coverage_reasons`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_doc_area_reasons`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_summary_facts_reasons`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_suite_rule_reasons`: 5 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_reasons_for_rule`: 14 branch(es), 14 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `inert_rules`: 2 branch(es), 2 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `inert_rule_names`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `evaluate_rule_liveness`: 1 branch(es), 1 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `__init__`: 1 branch(es), 0 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `is_empty`: 0 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `tags`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `all_tags`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `matched`: 1 branch(es), 1 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `sources`: 1 branch(es), 1 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | rule-engine | `edge_kind_count`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `live_edges_of_kinds`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `indexed_modules_under`: 1 branch(es), 1 exit form(s), over every call | none | yes | the liveness verdict for `forbid_import` is built here; it must tell a glob that can match nothing from one with nothing to ban now (#328) |
| branches | site-generation | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | graph | `_evaluate`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | rule-engine | `evaluate_all`: 34 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | no | caller's seat over an unchanged signature |


### `src/beadloom/application/gate_ownership.py`


> **Derived by:** `beadloom impact src/beadloom/application/gate_ownership.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 8 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:180` | none | no | `run_ci_gate` passes the findings through; the signature holds |
| callers | cli-commands | 2 — `src/beadloom/services/commands/federation.py:545` | none | yes | the surfaces that print "owned by" (#329) |
| callers | site-generation | 1 — `src/beadloom/application/site/raw_html.py:106` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | version-surface | 1 — `src/beadloom/doc_sync/version_surface.py:248` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| branches | gate-ownership | `derive_gate_ownership`: 1 branch(es), 4 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_attribute`: 0 branch(es), 1 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_owner_of`: 0 branch(es), 2 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_node_of`: 0 branch(es), 4 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_located_paths`: 0 branch(es), 2 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_documented_nodes`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `gate_ownership_lines`: 0 branch(es), 3 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_unowned_lines`: 0 branch(es), 2 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_claimed_clause`: 0 branch(es), 2 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | gate-ownership | `_unread_lines`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `owned`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `unowned`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `unattributed`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `none_owned`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | gate-ownership | `by_bead`: 0 branch(es), 1 exit form(s) | none | yes | ownership is attributed here; it moves from "a node covers the path" to "the bead changed the file", and the lines print the rule used (#329) |
| branches | ci-gate | `run_ci_gate`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | site-generation | `_opening_tag`: 0 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | version-surface | `read_version_surface`: 0 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_gate_ownership_lines`: 0 branch(es), 2 exit form(s), from a caller's seat | none | yes | the GitHub and rich surfaces of the attribution print the rule it was made by (#329) |
| branches | cli-commands | `_gate_ownership_notices`: 0 branch(es), 3 exit form(s), from a caller's seat | none | yes | the GitHub and rich surfaces of the attribution print the rule it was made by (#329) |


### `src/beadloom/application/declared_scope.py`


> **Derived by:** `beadloom impact src/beadloom/application/declared_scope.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 6 name-defined-more-than-once, 20 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | agent-prime | 1 — `src/beadloom/onboarding/scanner/alias_scan.py:207` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:933` | none | yes | `_step_scope_check` prints the base and the count of files attributed to the parent branch (#330); with #300 it resolves the pull request's branch in CI |
| callers | cli-commands | 5 — `src/beadloom/services/commands/docsync.py:78` | none | yes | `scope_check` gains `--base`; `sync_check --since` keeps its own ref |
| callers | document-pairs | 3 — `src/beadloom/doc_sync/document_pairs.py:410` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | flow-guards | 1 — `src/beadloom/application/guards/evaluation.py:86` | none | no | `evaluate_guard` reads the work item of the branch, not the base |
| callers | flow-suppression | 1 — `src/beadloom/onboarding/flow_suppression.py:130` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | git-activity | 1 — `src/beadloom/infrastructure/git_activity.py:196` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | graph-diff | 1 — `src/beadloom/graph/diff.py:510` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | graph-loader | 2 — `src/beadloom/graph/loader.py:154` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| callers | review-brief | 1 — `src/beadloom/application/review_brief/reachability.py:222` | none | yes | the brief takes its base from the same derivation, so #344's trunk base moves with it; the dev bead confirms by the callers of `trunk_ref` before its first commit |
| callers | rule-engine | 3 — `src/beadloom/graph/rules/scenario_coverage.py:66` | none | no | blast radius: the change edits no function of this node and the node owns nothing the change reaches |
| branches | declared-scope | `trunk_ref`: 1 branch(es), 1 exit form(s) | none | yes | the base of the judgement: merge-base with the parent branch, `--base`, trunk as the fallback, the base in the header (#330) |
| branches | declared-scope | `work_item_of_branch`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `scope_of_branch`: 1 branch(es), 5 exit form(s) | none | yes | the base of the judgement: merge-base with the parent branch, `--base`, trunk as the fallback, the base in the header (#330) |
| branches | declared-scope | `scope_check`: 1 branch(es), 3 exit form(s) | none | yes | the base of the judgement: merge-base with the parent branch, `--base`, trunk as the fallback, the base in the header (#330) |
| branches | declared-scope | `_key`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `_node_contexts`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `_target_nodes`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `work_item_axes`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `_section_of`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `_undecided`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `_unattributed`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | declared-scope | `checked`: 0 branch(es), 1 exit form(s) | none | yes | the base of the judgement: merge-base with the parent branch, `--base`, trunk as the fallback, the base in the header (#330) |
| branches | declared-scope | `describe`: 0 branch(es), 2 exit form(s) | none | yes | the base of the judgement: merge-base with the parent branch, `--base`, trunk as the fallback, the base in the header (#330) |
| branches | ci-gate | `_step_scope_check`: 1 branch(es), 3 exit form(s), from a caller's seat | none | yes | same |
| branches | flow-guards | `evaluate_guard`: 1 branch(es), 7 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | review-brief | `work_item_documents_channel`: 0 branch(es), 5 exit form(s), from a caller's seat | none | yes | same |
| branches | document-pairs | `_row_count_findings`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | document-pairs | `_kind_findings`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | document-pairs | `_unpaired`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | graph-diff | `_render_duplicates`: 0 branch(es), 0 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | graph-loader | `load_graph`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | graph-loader | `describe`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | graph-loader | `describe`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_matcher_description`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_node_leg`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | rule-engine | `_dead_reason`: 0 branch(es), 5 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | git-activity | `activity_history_note`: 0 branch(es), 3 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | flow-suppression | `render_suppression_notice`: 0 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | agent-prime | `_object_entries`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `sync_check`: 4 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_surface_lines`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `scope_check`: 0 branch(es), 1 exit form(s), from a caller's seat | none | yes | `--base` and the printed base (#330) |
| branches | cli-commands | `_emit_filter`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `waves`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |


### `src/beadloom/application/gate.py`


> **Derived by:** `beadloom impact src/beadloom/application/gate.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 11 dynamic-dispatch, 4 name-defined-more-than-once, 75 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/jvm_layout.py:411` | none | no | calls the Gate or a helper of it; the result type gains a status and loses nothing |
| callers | axes-section | 1 — `src/beadloom/doc_sync/axes_section.py:247` | none | no | calls the Gate or a helper of it; the result type gains a status and loses nothing |
| callers | cli-commands | 3 — `src/beadloom/services/commands/federation.py:418` | none | yes | `ci` writes the verdict through a pipe that may be non-blocking: the write survives EAGAIN and a crash is reported as a crash (#226, `beadloom-jwfc`) |
| callers | flow-guards | 4 — `src/beadloom/application/guards/checks/bead_claimed.py:48` | none | no | calls the Gate or a helper of it; the result type gains a status and loses nothing |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:889` | none | no | calls the Gate or a helper of it; the result type gains a status and loses nothing |
| callers | wave-plan | 1 — `src/beadloom/application/waves/media_checks.py:240` | none | no | calls the Gate or a helper of it; the result type gains a status and loses nothing |
| branches | ci-gate | `_run_doctor_checks`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_run_audit`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `run_ci_gate`: 1 branch(es), 1 exit form(s) | none | yes | the per-step exception boundary and the `ERROR` status (#318), so a crash in one step is a named step and not an aborted run |
| branches | ci-gate | `_step_reindex`: 1 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `lint_step`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_sync_check`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_sync_shape_finding`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_sync_summary`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_excused_clause`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_docs_audit`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_audit_summary`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_docs_quality`: 1 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_convention_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_issue_numbers`: 0 branch(es), 5 exit form(s) | none | yes | the summary states the open count by severity and the age rule (goal 8, S7) |
| branches | ci-gate | `_issue_number_summary`: 0 branch(es), 1 exit form(s) | none | yes | same |
| branches | ci-gate | `_issue_number_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_doc_spaces`: 1 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_named`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_doc_space_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_doc_quality_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_scope_check`: 1 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_scope_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_config_check`: 0 branch(es), 2 exit form(s) | none | yes | one verdict in a room, a worktree and the checkout, with the inputs and the comparison named (#334) |
| branches | ci-gate | `_step_doctor`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_doctor_summary`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_step_federate`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_simple_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_sync_finding`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_pair_clause`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_sync_unverified_finding`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_surface_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_audit_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_config_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_site_config_findings`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_activity_setting_findings`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_import_alias_findings`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_config_block_findings`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_mutation_scope_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_doctor_finding`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `_gate_failure_finding`: 0 branch(es), 1 exit form(s) | none | yes | the per-step exception boundary and the `ERROR` status (#318), so a crash in one step is a named step and not an aborted run |
| branches | ci-gate | `ok`: 0 branch(es), 1 exit form(s) | none | yes | the per-step exception boundary and the `ERROR` status (#318), so a crash in one step is a named step and not an aborted run |
| branches | ci-gate | `findings`: 0 branch(es), 1 exit form(s) | none | yes | the per-step exception boundary and the `ERROR` status (#318), so a crash in one step is a named step and not an aborted run |
| branches | flow-guards | `check_bead_claimed`: 1 branch(es), 3 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `check_working_branch`: 1 branch(es), 3 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `_could_not_run`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `_error_verdict`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | wave-plan | `_graph_drift_detail`: 2 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | axes-section | `_row`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | agent-prime | `_root_module_clusters`: 2 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | agent-prime | `_module_cluster`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | cli-commands | `ci`: 1 branch(es), 1 exit form(s), from a caller's seat | none | yes | same (#226) |
| branches | cli-commands | `_lines`: 1 branch(es), 5 exit form(s), from a caller's seat | none | yes | same (#226) |
| branches | cli-commands | `_verdict_on_the_generated_graph`: 2 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | mcp-server | `handle_complete_bead`: 2 branch(es), 4 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |


### `src/beadloom/services/commands/issue_number.py`


> **Derived by:** `beadloom impact src/beadloom/services/commands/issue_number.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 4 name-defined-more-than-once, 7 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/jvm_layout.py:411` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| callers | axes-section | 1 — `src/beadloom/doc_sync/axes_section.py:247` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:775` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| callers | cli-commands | 5 — `src/beadloom/services/commands/clean_room.py:315` | none | no | sibling commands share the helpers; `check` alone changes |
| callers | flow-guards | 3 — `src/beadloom/application/guards/evaluation.py:86` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| callers | site-generation | 7 — `src/beadloom/application/site/markdown_positions.py:266` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| callers | wave-plan | 1 — `src/beadloom/application/waves/media_checks.py:240` | none | no | calls a shared helper of this module (`_lines`, `_named`), not `check` |
| branches | cli-commands | `issue_number`: 0 branch(es), 0 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `allocate`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_refuse`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `check`: 1 branch(es), 1 exit form(s) | none | yes | a declared log that cannot be read exits non-zero, as the Gate step does (#331) |
| branches | cli-commands | `_exit_code`: 0 branch(es), 2 exit form(s) | none | yes | a declared log that cannot be read exits non-zero, as the Gate step does (#331) |
| branches | cli-commands | `_payload`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_named`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_refused_lines`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_refusal_lines`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `_undetermined_lines`: 0 branch(es), 1 exit form(s) | none | yes | a declared log that cannot be read exits non-zero, as the Gate step does (#331) |
| branches | cli-commands | `_lines`: 1 branch(es), 5 exit form(s) | none | yes | a declared log that cannot be read exits non-zero, as the Gate step does (#331) |
| branches | ci-gate | `_step_doc_spaces`: 1 branch(es), 3 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `evaluate_guard`: 1 branch(es), 7 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `_could_not_run`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | flow-guards | `_error_verdict`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_locate_lines`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_locate_html_block`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_locate_definition`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_code_block`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_definition`: 1 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `_checked`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | site-generation | `read`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | wave-plan | `_graph_drift_detail`: 2 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | axes-section | `_row`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | agent-prime | `_root_module_clusters`: 2 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | agent-prime | `_module_cluster`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | cli-commands | `_finish`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `mutation`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `rooms`: 0 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `typed_surface`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |
| branches | cli-commands | `version_surface`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |


### `src/beadloom/application/rooms.py`


> **Derived by:** `beadloom impact src/beadloom/application/rooms.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | unresolved: no declared sink is reached, so there is no commit point to co-write; the change adds none |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:180` | none | no | reads the census result; the result gains a source and a skip reason, loses nothing |
| callers | cli-commands | 4 — `src/beadloom/services/commands/federation.py:499` | none | yes | `rooms` and `_gate_room_lines` print the census; they must print the named skip (#332) |
| callers | gate-coverage | 1 — `src/beadloom/application/gate_coverage.py:225` | none | yes | `_read_pipeline` reads the pipeline the census derives legs from; the GitLab source must reach it or coverage reports over the GitHub file alone |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:836` | none | no | reads the census result; the result gains a source and a skip reason, loses nothing |
| callers | mutation-scope | 1 — `src/beadloom/application/mutation_scope/score.py:125` | none | no | reads the census result; the result gains a source and a skip reason, loses nothing |
| callers | source-derivation | 2 — `src/beadloom/application/source_derivation/call_graph.py:95` | none | no | reads the census result; the result gains a source and a skip reason, loses nothing |
| callers | wave-plan | 2 — `src/beadloom/application/waves/clean_room.py:309` | none | yes | `build_room` and `extras_a_room_installs` take the environment from the found project (#333, #311) |
| branches | verdict-room | `codec_in_force`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `requested_locale_name`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `codec_of_locale_name`: 1 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `locale_dimensions`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `current_room`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `room_line`: 4 branch(es), 1 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_locale_clause`: 0 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `derive_declared_rooms`: 1 branch(es), 1 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_read_packaging`: 2 branch(es), 2 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_floor_clause`: 0 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `project_distribution`: 1 branch(es), 2 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `canonical_distribution`: 1 branch(es), 1 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_installed_distributions`: 2 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_distributions`: 2 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_find_distribution`: 2 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_declared_requirements`: 2 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_record_requirement`: 7 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_closure`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `extras_satisfied_by`: 2 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `installed_extras`: 6 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_leg_extras`: 4 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `typed_extras_of_job`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `declared_extra_names`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `leg_installs`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_extras_of_command`: 3 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_uv_sync_extras`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_pip_project_extras`: 2 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_read_workflows`: 3 branch(es), 2 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `load_jobs`: 1 branch(es), 4 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_rooms_of_job`: 3 branch(es), 2 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_runs_on_of`: 3 branch(es), 3 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_matrix_os_key`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_matrix_of`: 3 branch(es), 2 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_canonical`: 0 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_combinations`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_resolve_runs_on`: 3 branch(es), 4 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `take_census`: 3 branch(es), 1 exit form(s), over every call | none | yes | `.gitlab-ci.yml` becomes a source of legs and Python projects are found under `scan_paths` by `**/pyproject.toml` (#332); a CI the census cannot read is a named skip, not `0 of 0` |
| branches | verdict-room | `_room_with_extras`: 1 branch(es), 2 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_compare`: 11 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_no_codec_note`: 0 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_locale_difference`: 2 branch(es), 5 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_extras_difference`: 3 branch(es), 3 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `_platform_of`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `label`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `label`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `entered`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | verdict-room | `not_entered`: 1 branch(es), 1 exit form(s), over every call | none | no | same node or caller's seat, a function the change does not edit |
| branches | ci-gate | `run_ci_gate`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | gate-coverage | `_read_pipeline`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | mutation-scope | `describe_room`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | source-derivation | `names_that_reach`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | source-derivation | `names_reached_from`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | wave-plan | `build_room`: 3 branch(es), 4 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | wave-plan | `extras_a_room_installs`: 4 branch(es), 3 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | cli-commands | `_gate_room_lines`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | cli-commands | `_format_gate_github`: 3 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | cli-commands | `rooms`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | cli-commands | `_human`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | yes | same |
| branches | mcp-server | `_verdict_room`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | caller's seat over an unchanged signature |


### `src/beadloom/application/waves/clean_room.py`


> **Derived by:** `beadloom impact src/beadloom/application/waves/clean_room.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 1 dynamic-dispatch, 6 name-defined-more-than-once, 9 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | co-writer through the YAML sinks the module reaches (`write_yaml_atomic`, `each_graph_file`); the change writes no YAML |
| callers | application | 1 — `src/beadloom/application/import_aliases.py:106` | none | no | calls `room_path` or `room_owner`; neither changes |
| callers | cli-commands | 2 — `src/beadloom/services/commands/clean_room.py:233` | none | yes | `clean_room` prints the "Measure in the room" hint from the project found, not from a template (#333) |
| callers | flow-guards | 1 — `src/beadloom/application/guards/invocation.py:282` | none | no | calls `room_path` or `room_owner`; neither changes |
| callers | graph | 3 — `src/beadloom/graph/go_modules.py:128` | none | no | calls `room_path` or `room_owner`; neither changes |
| callers | role-map | 2 — `src/beadloom/onboarding/role_map.py:350` | none | no | calls `room_path` or `room_owner`; neither changes |
| branches | wave-plan | `room_path`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `room_owner`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `room_request`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_record`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_names`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `room_invocation`: 0 branch(es), 1 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_interpreter`: 0 branch(es), 3 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `build_room`: 1 branch(es), 4 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_remembering`: 0 branch(es), 2 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_environment`: 1 branch(es), 2 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_refuse_the_room`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_refuse_the_request`: 0 branch(es), 2 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_refuse_carried`: 0 branch(es), 4 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_occupied`: 0 branch(es), 3 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_refused`: 0 branch(es), 1 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_head_commit`: 1 branch(es), 2 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_archive_head`: 1 branch(es), 0 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | wave-plan | `_within`: 0 branch(es), 1 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_carry`: 0 branch(es), 1 exit form(s) | none | yes | the environment from the found project's `uv.lock` and the hint derived from it (#333, #311); a carried path the tree no longer holds is a deletion in the room (#335) |
| branches | wave-plan | `_write_marker`: 0 branch(es), 0 exit form(s) | none | no | same node or caller's seat, a function the change does not edit |
| branches | flow-guards | `run_invocation`: 1 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | application | `_entry`: 0 branch(es), 4 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | graph | `_local_replacements`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | graph | `_workspaces`: 0 branch(es), 1 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | graph | `_directory`: 0 branch(es), 4 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | role-map | `_designations`: 0 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | role-map | `_inferred_rosters`: 0 branch(es), 0 exit form(s), from a caller's seat | none | no | caller's seat over an unchanged signature |
| branches | cli-commands | `clean_room`: 1 branch(es), 0 exit form(s), from a caller's seat | none | yes | same |
| branches | cli-commands | `waves`: 1 branch(es), 2 exit form(s), from a caller's seat | none | no | same node or caller's seat, a function the change does not edit |




## Decisions

### D1 — A gate that did not run is a failure, in the hook and in the Gate (S1; rulings 3, 2)

The composed pre-push hook exits non-zero with one sentence when `beadloom` is not on PATH
(today `exit 0` at the hook's head), and prints the Gate's verdict line or the words "the Gate
did not run" — never a sentence about stale documents for a crash. The pre-commit hook runs
`beadloom lint --strict` over the nodes that own a staged path (incremental reindex first;
measured budget: seconds on this repository, recorded in the bead), and its ruff leg stops hiding
stderr, tells `command not found` (exit 127) from violations (exit 1), and reads the
configuration of the Python project that owns the staged file (the nearest `pyproject.toml` or
`ruff.toml` above it). The Gate gains a per-step exception boundary: a step that raises becomes
`GateStep(status=ERROR)` with the exception's name and the step's name, the run continues, and
the verdict is red with "1 step(s) crashed" in its summary (#318). The `ci` command writes its
output through a writer that survives `EAGAIN` on a non-blocking pipe (retry on
`BlockingIOError`, the descriptor set blocking for the write), measured by a test that hands it a
non-blocking pipe (#226). The adopter's proposed `guard architecture` on `PostToolUse` is a
feature, filed as a bead outside this epic by the PRD's non-goal.

### D2 — Liveness tells "cannot match" from "nothing to ban now" (S1)

For `forbid_import` the liveness verdict has two sentences. A `to:` glob is *unmatchable* when
no path can satisfy it: syntax, or a literal prefix that is a source root of the project (the
project's own modules, which the rule's `from:` already covers). A `to:` glob that is matchable
but matches 0 of N indexed import paths is *live with nothing to ban*: the verdict reads
"0 imports of `os/**` in the project; the rule is live", at `info`, never `warn`. The test for
matchability is the matcher itself on a synthetic path built from the glob's literal prefix
(`os/**` → `os`, `bcrypt*` → `bcrypt`), so liveness and the matcher cannot disagree on "/"
again (#328). The same two sentences apply to `test_import_boundary`'s `to:`.

### D3 — Ownership by the files a bead changed (S1; amended 2026-10-19)

`derive_gate_ownership` attributes a finding to a bead by the files the bead's commits on the
branch changed, and by nothing else. A `refs:` declaration names graph nodes and no file, so it
attributes nothing (the clause "the paths its `refs:` name as files" of the approved text was
unimplementable as written and is withdrawn by the owner's ruling of 2026-10-19, S1R Minor 1).
A finding on a path no in-flight bead's commits changed is `unattributed`, never owned by the
neighbour whose node covers the directory. The summary line prints the rule: "owned by <bead>:
N finding(s), by the files the commits carrying `Bead: <id>` changed" (#329; D10 names the
binding). The branch's older commits (a parent branch not yet merged) are excluded by D4's base.

### D4 — The base is the merge-base with the parent branch (S1; ruling 4)

`trunk_ref` becomes `scope_base(project_root, *, explicit: str | None)`: `--base <ref>` when
given; else the merge-base with the branch the working branch was cut from, found as the
nearest branch (other than the working one) that contains the branch point, from
`git for-each-ref` and `git merge-base`; else the trunk (`origin/<trunk>` or `<trunk>`). The
header of `scope-check`, of the Gate's step and of `review-brief` prints the base and how many
files were attributed to the parent branch (#330, #344). In CI, the branch is resolved from the
pull request (`GITHUB_HEAD_REF`, GitLab's `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`) before the
checkout's own name, closing #300 (`beadloom-tsqz`).

### D5 — `issue-number check` exits as the Gate step does (S1)

A declared log that is missing or unreadable is exit 1 with the same sentence the Gate prints;
"no log declared" stays exit 0 with its sentence. The two surfaces share one function so they
cannot diverge again (#331).

### D6 — A monorepo's rooms and environment come from the project the census finds (S2)

`rooms` reads two sources of legs: `.github/workflows/*.yml` (today) and `.gitlab-ci.yml`
(jobs, `image:`, `script:` lines that install — `uv sync`, `pip install`, `npm ci`), each leg
carrying its source file. Python projects are found as every `pyproject.toml` under
`scan_paths` (the root included), each a *distribution* with its own `uv.lock` when present;
`clean-room` builds the environment of the distribution that owns the carried files, from its
`uv.lock` with `uv sync --frozen` (#311 at the root is the same rule), and derives the
"Measure in the room" hint from that distribution's test command (its `pyproject.toml`'s pytest
configuration or the leg's `script:`), never from a template. A project whose CI the census
cannot read gets "rooms: not derived — no readable pipeline" as a named skip in `ci`, not
`0 of 0`. A carried path the tree no longer holds is deleted in the room, and the room reports
the files where the tree differs from HEAD by more than this bead's commits (#335). A project
root below the git root is refused by `init` and `doctor` in words (#325, `beadloom-7pd6`).

Amended 2026-10-19 (owner's ruling on S2a's judgement call): which pipeline files the census
reads is declared, never guessed. `config.yml` carries `rooms.pipelines`, a list of `github`
and/or `gitlab`. Unset, the census reads every pipeline file the tree holds, each room carrying
its source; set, it reads the named ones only and lists a present file the key excludes as set
aside, naming the key; a name the key gives with no file in the tree is a named line in the
room block, not an error. The ordering S2a shipped (GitHub first, GitLab set aside when both
exist) is withdrawn. This repository declares `[github]` because its `.gitlab-ci.yml` is a
BDL-050 mirror no run takes, so its room set stays 33; the fixture declares nothing and keeps its
2 rooms. Measured by three tests: both files and no key → both sets; `[github]` → the GitLab file
set aside with the key named; `[gitlab]` with no `.gitlab-ci.yml` → the named line. A project
with both files and no key gains the GitLab rooms it never had: a finding-set move, additive.

### D7 — `config-check` names its inputs and gives one verdict wherever it runs (S2)

The composed `CLAUDE.md` is compared against a composition built from `flow.yml` and the
templates with the project's *declared* name (`config.yml`'s project name), never the
directory's name; a room, a worktree and the main checkout give the same verdict for the same
files; the finding names the file it composed from and the file it compared against (#334).
`sync-check` in a room without `.git` keeps #273's named skip.

### D8 — The version is MAJOR (ruling 5)

Three moves on inputs 9.0.0 accepts, each measured by a test that is red first: (1) the
pre-push hook without `beadloom` on PATH returns non-zero (was 0); (2) `issue-number check` on a
declared but missing log returns 1 (was 0); (3) `scope-check` on a branch cut from an unmerged
branch judges a different file set (the parent's files leave the diff). By the public-API guide
an exit-code move on an accepted input is MAJOR; the CHANGELOG names the three under Changed
with their measurements. Additive: `--base`, the `ERROR` step status, the `source` of a room, the
`measured_on` field of an issue-log entry (S7).

### D9 — Re-measurement is a slice with a protocol (S3; rulings 2, 7, 8)

Every open entry is re-run by its own `Command` on the version S2 ships, on this repository or on
the fixture its context names. Three outcomes, each written: *closed* — the issue is gone, the
archive gets the entry with a dated line of evidence (what was run, what it printed); *live* — a
bead under `beadloom-ba9w` with the entry's number in its title, the entry stays open until the
bead closes; *won't fix* — the owner's ruling with a reason, archived as a close. The slice's
output is the bead lists of S4–S7 and the stub lines for numbers 262 and higher; #196 and #288
are accounted for in the archive. Each surviving entry gains `measured_on: <date> <version>`,
read by the issue-log leg from S7 on.

### D10 — A commit is a bead's by its `Bead:` trailer (S1; owner's ruling 2026-10-19)

A commit belongs to a bead when its message carries the git trailer `Bead: <bead-id>`, and
only then; a bead id mentioned anywhere else in the message (a landing-lock note, a test bead
naming what it measured) binds nothing (S1R Minor 3). The composed commit format gains the
trailer — `[{ISSUE-KEY}] <type>: <description>` with `Bead: <bead-id>` in the trailer block —
in the flow template, so every adopter's `CLAUDE.md` and role files carry it after
`setup-agentic-flow`; this repository recomposes its own. Commits without the trailer are
`unattributed` under D3, which is the honest reading of a branch written before the rule.
Clarified 2026-10-19 (S1R second pass): git reads trailers from the message's final paragraph
only, so the trailer sits in the last paragraph beside any other trailer (`Co-Authored-By`, ...),
with no blank line between them and nothing after them; the composed format, both landing
fragments and the coordinator checklist say so and the example shows the two together. When a
claimed bead has no bound commit and a `Bead: <id>` line stands where git reads no trailer (outside
the final paragraph, or in a final paragraph git does not read as a trailer block), the
ownership report names those commits and where the line sits instead of denying the line
("N commit(s) carry `Bead: <id>` outside the message's final paragraph, where git reads no
trailer"). The reading needs git 2.22 or later; the gate-ownership DOC names it.
The JSON report's and the MCP tool's `claims` entry carries the same fact as a count and the
commit hashes (owner's ruling 2026-10-19), so a machine reader does not see `commits: 0` and nothing
else where the text surface names the misplaced line.

### D11 — Indexed paths are POSIX on every platform, and the surface ledger names its pairs (S2; added 2026-10-19 for #353)

The index writes a file's path as `Path.relative_to(root).as_posix()` at every write site
(`application/reindex/change_detection.py`, `application/reindex/indexing.py`), and every site
that matches a node's `source:` against the index normalises the declaration the same way before
it compares (`infrastructure/repository.py` `_owned_file_clause` and `source_covers`,
`doc_sync/engine.py` `_unchecked_reason`). On POSIX nothing changes; on Windows a directory
`source:` covers its files and a file `source:` matches its file, which today it does not (the
first outside adopter's teammate measured 167 declared pairs against 347 for one commit). The
index built by an older version is rebuilt by `reindex --full`, and `doctor` names an index
whose paths carry a backslash as one to rebuild. `.beadloom/sync-surface.json` carries the pair
list `(doc, file)` beside `declared_pairs`, so `sync-check` can name the pairs a platform or a
commit dropped instead of printing a smaller number. One test feeds backslash paths through the
three match sites; one indexes the monorepo fixture under a simulated Windows separator. The
Windows CI leg stays withdrawn (owner's decision of BDL-074); the two tests are the measurement.

### D12 — The landing lock's release reaches the trunk with the landing (S2; added 2026-10-19 for #354)

The slot is tracker state, exported into `.beads/issues.jsonl`, so its truth on the trunk is
whatever commit last exported it. The composed landing instruction says acquire before the
commit and release after, and says nothing about the push; an agent that releases after its push
leaves the trunk exporting a slot held by a closed bead, and the next clone's `acquire` is refused
with a holder nobody can wait on (the first outside adopter's second clone, 2026-10-19). The rule:
the sequence in the composed landing fragments and the coordinator checklist is acquire → commit
→ release → `bd export` → the export landed in the same landing (the bead's own last commit,
amended under the lock it still holds, or one more commit by path) → push. The pre-push hook
refuses to push a tree whose exported `issues.jsonl` holds the slot for the bead being pushed, and
names the sequence; `beadloom waves`'s `landing-order` medium reports a slot held by a closed bead
with the one remedy (`release --holder <closed-bead>`), because bd's own refusal offers `--wait`, a
queue nothing drains. One test pushes a tree whose export holds the slot and reads the refusal;
one plans a wave over a slot held by a closed bead and reads the remedy.

### D13 — The second tool reads the composed flow the first one reads (S2; added 2026-10-19 for #356)

The composer gains a `cursor` artifact kind beside `roles`, `commands`, `claude` and `docs`:
for a project whose `flow.yml` names Cursor, `setup-agentic-flow` composes the core, the project
layer and the STACK overlay — the same text `CLAUDE.md` carries — and the four commands into
`.cursor/rules/` as `alwaysApply` rules, replacing the stub; the role files stay shared. The
project layer's reach is stated in the flow documentation per kind (`roles` reaches every tool,
`claude` reaches Claude, `cursor` reaches Cursor), and `config-check` reports a tool whose
composition lacks a layer the other tool has, and stops naming `.claude/agents/<role>.md` as
missing on a project composed for Cursor alone. `setup-mcp` and `init --bootstrap` write a
portable MCP command (`beadloom` on PATH, as the composed instructions assume) and never
`shutil.which`'s absolute path; the composed `task-init` text names an absolute path outside the
document folder for the plan file, as the MCP `task_init` already does. Measured by a test that
byte-compares the rule bodies composed for the two tools, a test over a PATH without `beadloom`,
and a `config-check` red on a composition that lacks a layer. The refusals of (b) — a bead closed
with no COMPLETED measurement — are a behaviour rule agreed with the owner before code
(`beadloom-ujm0`, placed by S3); (c), (d) and (f) are features outside this epic.

## Public API (MAJOR)

- Exit codes: the pre-push hook without `beadloom` (0 → 1), `issue-number check` on a declared
  missing log (0 → 1), `scope-check`'s judged set on a branch cut from a branch.
- CLI: `scope-check --base <ref>` (additive); `ci` summary lines gain the base, the attribution
  rule, the room's source and the open-entry count by severity (additive text).
- `GateStep` gains the status `ERROR` (additive; consumers that switch on `passed`/`skipped`
  read it as not passed).
- `rooms` JSON gains `source` per room and a `not_derived` reason (additive).
- `config.yml` gains `rooms.pipelines` (additive); a project holding both pipeline files and declaring no key gains the GitLab rooms (a finding-set move, additive; D6 amended 2026-10-19).
- The MCP tool `complete_bead` no longer returns the verdict `unowned`; the ownership shape is the
  `ci` JSON's (`owned` / `unattributed`, S1c) — a vocabulary move (added 2026-10-19 from S1W).
- `config-check` exits 1 instead of 0 on role files composed before this release, because the
  flow template's commit format changed (D10): adopters re-run `setup-agentic-flow` — an
  exit-code move measured on the `0f1cb9a3` tree (added 2026-10-19 from S1W).
- The pre-push hook exits 1 on a tree whose export holds the slot for the pushed bead (an
  exit-code move on an input 9.0.0 accepted, D12).
- `sync-surface.json` gains the pair list beside `declared_pairs` (additive); indexed paths are
  POSIX on every platform (a finding-set move on Windows only, D11).
- `setup-agentic-flow` writes `.cursor/rules/` rules in place of the stub on a project naming Cursor (a file-set move, D13); `config-check` exits 1 on a composition that lacks a layer the other tool has (an exit-code move on an input 9.0.0 accepted); `setup-mcp` and `init --bootstrap` write `beadloom` instead of an absolute path (a text move in a generated file).
- `waves` exits 1 on a landing slot held by a bead the tracker lists closed, naming the release (an
  exit-code move, D12; added 2026-10-20 from S2g).
- `clean-room --carry <path>` where HEAD holds the path and the tree does not builds the room with
  the path deleted (2 → 0/1, also for a path `--rebuild` remembers; D6); `--json` gains `deleted`,
  `not_carried` and a third `limits` entry (additive; added 2026-10-20 from S2d).
- `config-check` and `ci` in a worktree or a room exit 0 instead of 1 on a project whose root
  manifest does not name it (an exit-code move, D7); `config.yml` gains `project_name:` (additive);
  the verdict names the composed-from and compared-against files (additive text; added 2026-10-20
  from S2c).
- `init`, `doctor` and `sync-check --since` exit 1 on a project root below the git root (an
  exit-code move on an input 9.0.0 accepted; #325, S2e).
- `doctor` exits 1 on any `ERROR` row, not only the git-root one (an exit-code move generalised
  in S2e; the owner's ruling pending, S2R Minor 1).
- `rules.yml`: no vocabulary change in S1–S2; liveness findings for `forbid_import` change
  level from `warn` to `info` when live with nothing to ban (a finding-set move, named).
- The issue-log entry format gains `measured_on` (S7, additive); the leg's summary adds the
  count by severity and the age rule.

## Slices

- **S1 — gates that lie** (D1–D5, D8): dev beads: hooks (#326, #327); liveness (#328);
  ownership (#329); base (#330, #300, #344); Gate boundary and the pipe-safe writer (#318,
  #226); `issue-number check` exit (#331); the adopter fixture (`backend/pyproject.toml` +
  `uv.lock`, `frontend/`, `.gitlab-ci.yml`, one domain and one feature with the same subpackage
  name, two spec files beside code) under `tests/fixtures/` for S1–S4 to measure on. Then test,
  review, tech-writer, PR.
- **S2 — the monorepo on GitLab** (D6, D7): dev beads: rooms from two sources and nested
  distributions (#332); the room's environment and hint (#333, #311); `config-check` (#334);
  carry deletions and the HEAD-difference report (#335); the nested-root refusal (#325); POSIX
  paths in the index and the pair list in the surface ledger (#353, D11); the lock's release
  landed before the push (#354, D12); the Cursor composition, the portable MCP command and the
  plan path (#356, D13). Then test, review, tech-writer, PR.
- **S3 — re-measurement** (D9): measurement beads by area — Gate and CI; doc-sync; rules and
  lint; init and scanning; site and viewer; the rest — each closing, filing or ruling its
  entries; one bead writes the archive and the stubs. Review, PR. No dev bead.
- **S4 — the false-stale family** (#338, #339, #342, #346–#349, `beadloom-r9t5`): designed from
  S3's result; its axes appended here.
- **S5 — the original debt A–D** (2026-10-08's measures): designed from S3's result.
- **S6 — the tooling baseline E–I** (bd 1.3.x with the claim / was / is table and the Dolt
  remote scenario; the agents' capability check; dependencies and their automation; context rot;
  `ctx` and the Gate's applicability): designed from S3's result; E first, because the team
  model's measurement 7 waits on it.
- **S7 — the rest and the recurrence** (goal 7's ruled beads; `measured_on` and the age rule in
  the issue-log leg; the count by severity in the summary; the release role's "tooling
  baseline" duty; the ROADMAP re-ranked; close-out).
