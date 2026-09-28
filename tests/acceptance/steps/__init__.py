"""Step implementations, one folder per node, mirroring the feature files.

A step file lives in ``steps/<domain>/<node>/``, the folder of the node whose
feature files it loads, spelled as that node's folder under ``docs/`` is. A step
file that loads feature files of two or more nodes lives in ``steps/common/``.

Most node folders are hyphenated (``wave-plan``, ``doc-sync``), which is not a
Python identifier. pytest therefore stops its package walk at such a folder and
imports the step module under its own file name, with that folder put on
``sys.path``. The ``__init__.py`` files there exist for the linter, which
otherwise reads ``tests`` as a third-party import. The consequence to keep in
mind: two step files in node folders must not share a file name, or collection
stops with an "import file mismatch" error.
"""
