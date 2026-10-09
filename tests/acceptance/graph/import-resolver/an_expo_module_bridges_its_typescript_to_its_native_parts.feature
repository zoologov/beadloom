# BDL-080 S3b (`beadloom-wbqd`), RFC D5 (e). An Expo module's TypeScript reaches its Swift
# and Kotlin through no import: `requireNativeModule('HapticPulse')` names the native module
# by a string, and the only file that says which native code answers is the module's
# `expo-module.config.json`. Measured before this bead on the synthetic app of
# `tests/support/expo_module_tree.py`, with a node per module and per native folder: the
# reindex derived no edge between a module and its native parts (the first two scenarios
# below were red on that code for that reason).
#
# The edge is derived on every reindex, as the import edges are, and not written into the
# graph YAML: a platform the config stops naming stops being bridged.

@bead:beadloom-wbqd @node:import-resolver
Feature: an Expo module's config bridges its TypeScript to its native parts

  Scenario: a module linked on both platforms uses its Swift part and its Kotlin part
    Given an Expo app with a node for each module and for each native folder
    When the project is indexed
    Then the derived uses edges are exactly "haptic-pulse -> haptic-pulse-ios", "haptic-pulse -> haptic-pulse-android", "screen-lock -> screen-lock-ios"

  Scenario: the edge names the config and the native modules it was read from
    Given an Expo app with a node for each module and for each native folder
    When the project is indexed
    Then the uses edge "screen-lock -> screen-lock-ios" was read from "modules/screen-lock/expo-module.config.json" for "ios", naming "ScreenLockModule"

  Scenario: a platform the config does not link is not bridged
    Given an Expo app whose module holds an android folder its config does not link
    When the project is indexed
    Then no uses edge points at "screen-lock-android"

  Scenario: a native folder no node of its own owns yields no edge
    Given an Expo app with a node for each module and no node for its native folders
    When the project is indexed
    Then the project has no derived uses edge

  Scenario: a platform removed from the config is no longer bridged on the next reindex
    Given an Expo app with a node for each module and for each native folder
    And the project is indexed
    When the android block is removed from the config of "modules/haptic-pulse"
    And the index is updated incrementally
    Then no uses edge points at "haptic-pulse-android"
    And every derived uses edge equals a fresh index of the same tree
