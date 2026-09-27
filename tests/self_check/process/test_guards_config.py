"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_guards_config.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import yaml

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.config import (
    load_guards_config,
)
from tests.support.repository_root import REPO_ROOT


class TestEventRoutingIsNotDeclaredHere:
    """``on:`` is gone from the schema — deleted, not quoted (owner decision, 2026-08-22).

    It was a documented capability wired to nothing: ``GuardSpec.events`` was
    written by the loader and read by no code path, while which tool calls count
    as an edit lives in the harness matcher. Standing rule 8 — a permission
    without a caller is not a capability — makes that a defect in the product,
    not only in the docs, so the key is removed rather than spelled correctly.
    Quoting it would have kept the promise and added nothing behind it.

    It returns, wired to a consumer, in S3 where composition and adapters are
    reworked.
    """

    def test_the_shipped_dogfood_config_declares_no_events(self) -> None:
        """Our own flow.yml must not teach an incantation that does nothing."""
        repo_root = REPO_ROOT
        body = yaml.safe_load((repo_root / ".beadloom" / "flow.yml").read_text(encoding="utf-8"))

        for name, declared in (body.get("guards") or {}).items():
            keys = set(declared or {})
            assert "on" not in keys, name
            # YAML 1.1 reads a bare `on` as the boolean True — the spelling that
            # made the dead key invisible in the first place.
            assert True not in keys, name


class TestAnUnknownKeyInAGuardBodyIsRejected:
    """A key the loader does not read is a typo, and a typo here changes enforcement.

    The module already refuses an unknown guard NAME and an unknown strictness
    VALUE for one reason — a gate must not be switched off by a spelling. An
    unknown KEY was the hole in that reasoning, and it is not symmetric:

    * ``exclude:`` for ``exclusions:`` parses with zero exclusions, so the guard
      OVER-guards — the safe direction;
    * ``option:`` for ``options:`` drops the declared ``trunk``, and
      ``working-branch`` then compares against the shipped default ``main``.
      Measured through the real binary on a project whose trunk is ``develop``:
      an edit made directly ON ``develop`` answered ``PASS — on working branch
      'develop' (trunk is 'main')`` at exit 0, i.e. the guard passed the one
      situation it exists to catch.

    The mitigation (the verdict prints the trunk it compared against) is on the
    stream and the exit code a hook harness discards: a ``pass`` at 0 is shown to
    nobody. So the typo is answered where it is made, in the file, not left to an
    attentive reader of a line that is never displayed.
    """

    def test_the_config_this_repository_ships_still_parses(self) -> None:
        """No adopter's green project turns red on upgrade — starting with our own.

        Guards shipped in 3.0.0, so an adopter's ``flow.yml`` can now carry a
        ``guards:`` block — which is what makes this check load-bearing rather
        than a note about our own file. Every guard this repository declares
        must still be a built-in and must still parse, and it is checked here
        rather than assumed. (Until 3.0.0 the reason given was that no
        published ``flow.yml`` had the block at all; that sentence stopped being
        true at the release and is replaced rather than left standing.)
        """
        repo_root = REPO_ROOT

        config = load_guards_config(repo_root)

        assert set(config.declared_names()) <= set(BUILTIN_GUARDS)
        assert config.spec_for("working-branch").options["trunk"] == "main"
