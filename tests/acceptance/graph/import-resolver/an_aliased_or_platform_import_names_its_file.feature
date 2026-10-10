# BDL-080 S3a (`beadloom-cwzc`), RFC D5 (a)-(d). Measured by the brief of 2026-10-08 (Q9):
# a non-relative JS/TS specifier resolved only through two hard-coded prefixes, `@/` and
# `~/` read as `src/`, so a project whose `tsconfig` maps `@/*` elsewhere, or whose Babel
# `module-resolver` or Vite `resolve.alias` declares `@shared`, got no edge for those
# imports. A React Native module that exists only as `Button.ios.tsx` and
# `Button.android.tsx` was named by no candidate, and a `.mjs` module's own imports were
# never read, because the indexer had no grammar for `.mjs` or `.cjs`.
#
# The fixtures are frontends this repository cannot be mistaken for: a Vue app whose
# `@/*` lives in `tsconfig.app.json`, written with comments and trailing commas, and an
# Expo-like app whose `@/*` names the project root and whose Babel aliases are declared
# under `imports.aliases:`.

@bead:beadloom-cwzc @node:import-resolver
Feature: an aliased or platform-suffixed import names the file it reaches

  Scenario: a tsconfig paths entry resolves an import to the node owning its file
    Given a Vue app whose tsconfig.app.json maps "@/*" to "./src/*"
    When the project is indexed
    Then the import "@/features/cart" of "src/widgets/header/ui/Header.vue" resolves to "cart"
    And the import "src/shared/config/tokens" of "src/app/main.ts" resolves to "config"

  Scenario: an alias declared under imports.aliases resolves an import
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    When the project is indexed
    Then the import "@shared/api" of "src/entities/profile/model/profile.ts" resolves to "api"
    And the import "~/features/auth" of "app/settings.tsx" resolves to "auth"

  Scenario: a tsconfig paths entry wins over the hard-coded reading of "@/"
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    When the project is indexed
    Then the import "@/components/ThemedText" of "app/index.tsx" resolves to "components"

  Scenario: a module that exists only with platform suffixes is resolved
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    When the project is indexed
    Then the import "./Button" of "src/shared/ui/Button/index.ts" resolves to "ui"
    And the import "../../../shared/lib/haptics" of "src/entities/profile/ui/ProfileCard.tsx" resolves to "lib"

  Scenario: a .mjs module is parsed, so its own imports are recorded
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    When the project is indexed
    Then the import "@shared/lib/haptics" of "src/shared/config/env.mjs" resolves to "lib"

  Scenario: a specifier no alias and no file answers stays recorded with no node
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    When the project is indexed
    Then the import "@shared/missing" of "src/shared/api/client.ts" is recorded with no node
    And the import "react-native" of "components/ThemedText.tsx" is recorded with no node

  Scenario: an incremental index after tsconfig changes equals a fresh index
    Given a Vue app whose tsconfig.app.json maps "@/*" to "./src/*"
    And the project is indexed
    When tsconfig.app.json is rewritten to map "@/*" to "./lib/*" and the index is updated
    Then the import "@/features/cart" of "src/widgets/header/ui/Header.vue" resolves to "legacy-cart"
    And every resolved import and every derived edge equals a fresh index of the same tree

  Scenario: an incremental index after imports.aliases changes equals a fresh index
    Given an Expo-like app whose Babel aliases are declared under imports.aliases
    And the project is indexed
    When the "@shared" alias is pointed at "legacy/shared" and the index is updated
    Then the import "@shared/api" of "src/entities/profile/model/profile.ts" resolves to "legacy-api"
    And every resolved import and every derived edge equals a fresh index of the same tree
