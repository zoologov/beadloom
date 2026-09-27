# The locale a room is running under, and a name that resolves to another room
# (BDL-068 S6, BDL-UX #248 and #249). One Feature per file.

@bead:beadloom-0mdo.50 @node:verdict-room
Feature: a room states the locale it is running under

  This project has been bitten by its locale leg three times — BDL-061 S2, PR #61
  and PR #62 — and each time the reproduction was possible on a developer machine
  and was not made, or was made in the wrong room. The census could not help: it
  derived the platform and the interpreter and no locale at all, so `beadloom
  rooms` answered "this run cannot describe the dimension `locale`" while the
  process genuinely was running under an ASCII codec.

  A locale NAME is not a room. `en_US.ISO-8859-1` is the name `ci.yml` publishes,
  and macOS has no locale by that spelling: setting it falls back to ASCII, so a
  developer reproducing the 8-bit leg runs the C room a second time under the
  other room's name. Measured on Darwin 25.6.0 arm64, CPython 3.13.7, with
  PYTHONUTF8=0 and PYTHONCOERCECLOCALE=0: `en_US.ISO-8859-1` gives preferred
  encoding `ascii` and `en_US.ISO8859-1` gives `iso8859-1`.

  So the dimension is the CODEC in force, derived the way `ci.yml`'s own
  anti-vacuity step derives it, and never the name somebody spelled. A room that
  silently becomes a different room is a phantom room, and the census is what
  refuses to report it as entered.

  Scenario: the room this run is in names the codec its locale chose
    Given a workflow job declaring a locale leg
    When the rooms are reported
    Then the room this run is in names a locale dimension

  Scenario: a leg declaring the locale this run is under is entered
    Given a workflow job declaring this run's own platform, interpreter and locale
    When the rooms are reported
    Then that leg is reported as entered

  Scenario: a leg declaring another locale is not entered, and says which codec
    Given a workflow job declaring a locale leg
    When the rooms are reported
    Then that leg is reported as not entered
    And the reason names the codec the leg declares and the one this run is in

  Scenario: a locale name that did not apply here is not a room this run entered
    Given a child process asked for a locale no platform has
    When that child reports its rooms
    Then the leg declaring that locale is reported as not entered
    And the report says the name did not apply and names the room the run is in

  Scenario: a leg whose locale names no codec is unresolved rather than compared
    Given a workflow job declaring a locale that names no character encoding
    When the rooms are reported
    Then that leg is reported as not entered
    And the report names it as unresolved

  Scenario: locale is an axis a checklist can loop over
    Given a workflow job declaring a locale leg
    When the locale axis is asked for
    Then the locale that leg declares is printed
