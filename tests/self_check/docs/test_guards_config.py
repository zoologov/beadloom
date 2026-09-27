"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_guards_config.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import yaml

from tests.support.repository_root import REPO_ROOT


class TestNothingRoutesOnAnEvent:
    """The SPEC's claim, checked against behaviour rather than against a grep.

    SPEC.md: "event routing is not Beadloom's today ... Beadloom is told
    'evaluate this guard for this context'; it is not told, and does not decide,
    what happened." If any code path had quietly kept reading the event, the
    verdicts below would differ.
    """


    def test_the_spec_declares_no_on_key_in_its_schema_example(self) -> None:
        """Parsed, not grepped: the prose says the words "no ``on:`` key"."""
        spec_path = (
            REPO_ROOT
            / "docs"
            / "domains"
            / "application"
            / "features"
            / "flow-guards"
            / "SPEC.md"
        )
        text = spec_path.read_text(encoding="utf-8")
        blocks = [
            block.split("```", 1)[0]
            for block in text.split("```yaml")[1:]
        ]

        assert blocks, "the SPEC must still show a guards: schema example"
        for block in blocks:
            body = yaml.safe_load(block) or {}
            for name, declared in (body.get("guards") or {}).items():
                keys = set(declared or {})
                assert "on" not in keys, name
                assert True not in keys, name
