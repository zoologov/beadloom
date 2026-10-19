# Test fixtures

`monorepo/` is the monorepo fixture: the layout of the first outside adopter, anonymised, which
BDL-083 S1 to S4 measure on. The git root is the project root. A Python backend lives under
`backend/` with its own `pyproject.toml` and `uv.lock`, and a Feature-Sliced frontend lives
under `frontend/` with two spec files beside the code. The pipeline is `.gitlab-ci.yml`, and
the repository has no `.github/`. The domain `digest` and the feature `application-digest`
share the subpackage name `digest`, and `.beadloom/` holds the configuration and graph the
adopter wrote after `init`. A test copies it with `monorepo_checkout` from
`tests/support/monorepo_fixture.py`, which restores the names stored under `.fixture` and
commits the copy. The node set, the
reindex, `lint --strict` and `sync-check` on the copy are asserted in
`tests/integration/application/reindex/test_the_monorepo_fixture_indexes.py`. No colleague or
owner project is named in it, and an edit that adds such a name is a defect.
