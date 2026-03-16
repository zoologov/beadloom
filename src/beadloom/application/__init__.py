"""Application layer — use-case orchestration services.

This layer sits between the interface layer (``services``/``tui``) and the
domain layer (``context_oracle``, ``doc_sync``, ``graph``, ``onboarding``).
It contains orchestrators that coordinate multiple domains plus infrastructure
to fulfil a use case — they hold no business rules of their own.

Modules (``reindex``, ``doctor``, ``debt_report``, ``watcher``) are NOT
eagerly re-exported here: they have cross-domain dependencies and eager
import would risk circular imports.  Import them directly::

    from beadloom.application.reindex import reindex, incremental_reindex
    from beadloom.application.doctor import run_checks
    from beadloom.application.debt_report import collect_debt_report
    from beadloom.application.watcher import watch
"""
