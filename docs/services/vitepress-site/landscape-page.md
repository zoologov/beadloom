# Landscape page (component)

A slice of the `pages` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/pages/landscape/`

---

## Overview

`LandscapeMap`, the component the generated `landscape.md` mounts: the map of the contracts
between services. Since BDL-076 A4 it is a thin page over the graph viewer in its `landscape`
mode, 560 pixels high. The viewer owns the toolbar, with the protocol, verdict and "Only problems"
filters in the mode's slot, the neighbourhood and impact modes, navigation, full screen and URL
state. The page puts `LandscapeCard` in the viewer's panel.

`LandscapeCard` is the service card. It shows the service's kind, its health, the number of
contracts it takes part in and a link to its page, and then every contract it produces or
consumes. A declared contract shows its protocol, verdict, routing (AMQP exchange, routing key
and message type, or the GraphQL schema), its surface (the fields each side names, or the AMQP
body the producer declares) and, under "Breaking", the references the consumer makes that the
producer does not serve. A surface that was not
declared reads "undeclared", never an invented field. A contract with no declared protocol is
shown as a plain dependency with its verdict. Each contract lists its producers and consumers,
and a click on one selects that service. There is no edge card: a contract is reached from the
card of either of its ends.

## Public API

- `LandscapeMap` (Vue component, no props).

## Depends on

- `site-graph-viewer` (widgets).
- `site-landscape-data` (entities).

## Tests

`src/beadloom/site_scaffold/e2e/landscape.spec.js` drives this page.
