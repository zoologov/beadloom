# BDL-080 S3b (`beadloom-wbqd`), RFC D5 (e). Measured before this bead on the synthetic app
# of `tests/support/expo_module_tree.py`: init gave the Kotlin of `haptic-pulse` to the
# JVM layout, as a module node and a package node part of the ROOT rather than of the
# Expo module; it gave the Swift of `haptic-pulse` no node and no scan path, and printed
# "Not read: 2 .swift files outside any Package.swift target"; it left the module's own
# `index.ts` unread because the folder "holds a module"; and the first reindex drew no
# edge between a module and its native code.

@bead:beadloom-wbqd @node:agent-prime
Feature: init writes an Expo module and its native parts, and the reindex bridges them

  Background:
    Given an Expo app with local Expo modules on iOS and Android
    When beadloom init is run with --bootstrap

  Scenario: each Expo module is a component holding one component per native folder
    Then the node "haptic-pulse" is a component with source "modules/haptic-pulse/" and part of the root
    And the node "haptic-pulse-ios" is a component with source "modules/haptic-pulse/ios/" and part of "haptic-pulse"
    And the node "haptic-pulse-android" is a component with source "modules/haptic-pulse/android/" and part of "haptic-pulse"
    And the node "screen-lock-ios" is a component with source "modules/screen-lock/ios/" and part of "screen-lock"
    And no node is written for the folder "modules/screen-lock/android/"

  Scenario: the module's code, Swift and Kotlin are all read
    Then init does not report a file it did not read
    And the scan paths hold "modules/haptic-pulse" and "modules/screen-lock"

  Scenario: the first index after init bridges each module to its native parts
    Then init wrote no uses edge into the graph YAML
    And the index holds the uses edges "haptic-pulse -> haptic-pulse-ios", "haptic-pulse -> haptic-pulse-android", "screen-lock -> screen-lock-ios"
