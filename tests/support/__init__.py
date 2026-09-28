"""Helpers the test modules share (BDL-074 B1).

A test module never imports another test module: what two of them need lives
here, under a name that says what it is for. That is what lets a test file move
to any folder without taking a neighbour's definitions with it.
"""
