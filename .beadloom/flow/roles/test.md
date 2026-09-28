
## Project layer — this repository's test suite (`.beadloom/flow/roles/test.md`)

Everything above ships to every adopter. Everything below is true of **this repository
only** and is never distributed.

- **Two guards run with every test.** `tests/conftest.py` starts each test in its own empty
  directory, so a test that leaves its root to the `Path.cwd()` default fails here instead of
  passing by accident. The contact guard fails a test that opens this checkout's
  `.beadloom/beadloom.db` or runs `bd` or `git` against it, and its allowed list is empty.
- **A fourth kind, `tests/self_check/`,** holds the assertions about this repository's own
  files, in four folders: `architecture` (its graph, rules and code structure), `config` (its
  manifest, CI workflows and declared configuration), `docs` (its documents and site) and
  `process` (its roles, commands, hooks, tracker and the suite's own discipline). Every test
  there carries the `self_check` marker by its folder. One that needs a built index takes the
  `self_check_snapshot` fixture, a reindexed copy of the tree, and never the live index.
- **The checkable standards are checked**, over every file of the suite:
  `tests/self_check/architecture/test_the_suite_shares_helpers_through_support.py` fails on
  an import of a test module and on a file that counts its own parents, and
  `tests/self_check/architecture/test_a_test_file_is_named_by_its_behaviour.py` fails on a
  work-item id in a test file's name. Each keeps an exemption list whose every entry states a
  reason and an exit, and an entry that no longer matches fails, so the lists only shrink.
- **The root helper is `tests/support/repository_root.py`** (`REPO_ROOT`, `TESTS_ROOT`).
- **A moved or renamed test file is renamed in the mutation pool too.** The pool is the
  `[tool.mutmut]` test selection in `pyproject.toml`, and
  `tests/self_check/config/test_mutation_runner_scope.py` fails on an entry that no longer
  exists.
