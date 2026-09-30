# beadloom:domain=application
# beadloom:feature=site-generation
"""The portal: everything ``beadloom docs site`` generates, owned by ``site-generation``.

BDL-076 K1 (``beadloom-ujzb.2``) gathered the portal's modules here from
``application/``, so the ``site-generation`` node owns them as one package and
their symbols are no longer counted against the ``application`` domain. Each
module keeps one responsibility:

- :mod:`.generate` — the ``docs site`` use case, writing the whole content tree;
- :mod:`.architecture_view` / :mod:`.architecture_card` — ``architecture.data.json``,
  the graph placement and the node card;
- :mod:`.landscape_view` — ``landscape.data.json``, the interactive landscape data;
- :mod:`.landscape_map` — the Mermaid landscape map page;
- :mod:`.node_pages` — one Markdown page per graph node;
- :mod:`.nav` — the VitePress nav and sidebar trees;
- :mod:`.about` — the README rendered as the About page;
- :mod:`.markdown_links` — the links in a project's own text, rebased onto the portal;
- :mod:`.markdown_code` — where a project's Markdown holds code, left as written;
- :mod:`.project_text` — a project's own text on a page, shown as written rather
  than compiled as a Vue template;
- :mod:`.published_docs` — the ``docs/`` tree published with validation badges;
- :mod:`.mermaid_guard` — the generation-time Mermaid validity guard;
- :mod:`.metrics_history` — the append-store behind the dashboard's trends;
- :mod:`.dashboard` — the metrics dashboard data and page.

``generate_site`` is re-exported so ``from beadloom.application.site import
generate_site``, the entry the CLI uses, reads as it did before the move.
"""

from __future__ import annotations

from beadloom.application.site.generate import generate_site

__all__ = ["generate_site"]
