"""Beadloom CLI command groups.

Cohesion-driven decomposition of the former ``services/cli.py`` monolith
(BDL-059 S4). Each module owns one nameable command responsibility and registers
its commands onto the shared ``main`` Click group defined in :mod:`._root`. The
``cli`` registration entry (:mod:`beadloom.services.cli`) imports these modules
to wire every command, keeping ``from beadloom.services.cli import main`` stable.
"""
