# BDL-080 S3e (`beadloom-af99.12`). Measured by S3d (`beadloom-chdx`) on a Vue 3 prototype:
# on a case-insensitive filesystem (macOS) `./app` from `src/main.ts` beside `src/App.vue`
# resolved to App.vue, because the `.vue` candidate precedes the folder index and
# `src/app.vue` answered `is_file()` for `src/App.vue`; on Linux the same import resolved
# to `src/app/index.ts`. One tree indexed two ways. The bundler agrees with Linux: Vite's
# default `resolve.extensions` holds no `.vue`, so `./app` loads `app/index.*` on macOS too.

@bead:beadloom-af99.12 @node:import-resolver
Feature: a JS/TS specifier names a file by its exact case, on every filesystem

  Background:
    Given a Vue app with src/App.vue beside the folder src/app/ entered through its index
    When the project is indexed

  Scenario: a relative specifier names the folder index, not a file that differs in case
    Then the import "./app" of "src/main.ts" resolves to "app"

  Scenario: an aliased specifier names the folder index, not a file that differs in case
    Then the import "@/app" of "src/router.ts" resolves to "app"

  Scenario: a specifier written in the file's own case still names the file
    Then the import "./App.vue" of "src/main.ts" resolves to "storefront"
