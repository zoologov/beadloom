"""BDL-050 BEAD-03: the consolidated CI structure mirrors across GitHub + GitLab.

These are static, network-free YAML checks asserting the consolidated pipeline
shape introduced in BDL-050:

* ``.github/workflows/ci.yml`` — jobs ``gate`` / ``tests`` (3.10-3.13 matrix) /
  ``site-build`` / ``ai-techwriter`` (``needs: [gate, tests, site-build]``).
* ``.gitlab-ci.yml`` — stage ``verify`` (``gate`` / ``tests`` matrix /
  ``site-build``) + stage ``docs`` (``ai-techwriter`` with
  ``needs: [gate, tests, site-build]`` and the merge_request_event rule).
* the vendored ``ai_techwriter`` templates — restructured to the SAME
  consolidated model so a scaffolded repo gets the consolidated pipeline.

This module holds the product half: every property over the two templates. The
same properties over this repository's own pipelines are self-checks, in
``tests/self_check/config/test_ci_consolidated_structure.py``, and both run the
one body each property has in :mod:`tests.support.ci_pipeline_properties`
(BDL-074 F3).
"""

from __future__ import annotations

from tests.support import ci_pipeline_properties as properties
from tests.support.ci_pipeline_properties import held_to
from tests.support.ci_workflows import GH_TEMPLATE, GL_TEMPLATE

#: The rows the properties below run over: the templates an adopter receives.
GH_TEMPLATES = (GH_TEMPLATE,)
GL_TEMPLATES = (GL_TEMPLATE,)

test_github_has_all_consolidated_jobs = held_to(
    properties.github_has_all_consolidated_jobs, GH_TEMPLATES
)
test_github_tests_matrix_covers_3_10_to_3_13 = held_to(
    properties.github_tests_matrix_covers_3_10_to_3_13, GH_TEMPLATES
)
test_github_ai_techwriter_needs_the_three_verify_jobs = held_to(
    properties.github_ai_techwriter_needs_the_three_verify_jobs, GH_TEMPLATES
)
test_gitlab_declares_verify_and_docs_stages = held_to(
    properties.gitlab_declares_verify_and_docs_stages, GL_TEMPLATES
)
test_gitlab_verify_stage_jobs = held_to(properties.gitlab_verify_stage_jobs, GL_TEMPLATES)
test_gitlab_tests_matrix_covers_3_10_to_3_13 = held_to(
    properties.gitlab_tests_matrix_covers_3_10_to_3_13, GL_TEMPLATES
)
test_gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs = held_to(
    properties.gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs, GL_TEMPLATES
)
test_gitlab_ai_techwriter_runs_on_merge_request = held_to(
    properties.gitlab_ai_techwriter_runs_on_merge_request, GL_TEMPLATES
)
