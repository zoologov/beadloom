# Layers (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/layers/`

---

## Overview

The layers of the architecture graph, read from the data file rather than named in code.

**Every layer rule is drawn (BDL-080 S1c).** A data file that carries `layer_rules` names the
layers of each rule, and each node names the rule that places it (`layer_rule`) and its rank
there (`layer_rule_rank`). A layer is the pair (rule, rank): a project with a backend and a
frontend has two orders, and rank 2 of one is no layer of the other. A file without
`layer_rules`, version 1 or a version 2 file written before BDL-080, names one order: its
declared `layers: [{ name, rank, tag, token }]`, else the `layer_rank` values that occur, each
named by the `layer` token of a node that declares it. Such a file is drawn as it was before.

**A rule is named two ways (BDL-080 S1e).** Its `name` is its identifier: lint reports it, and
the Layer filter's value and the URL carry it, so a link stays good when a title is reworded.
Its `title`, where it declares one, is what a reader is shown in the legend heading, the filter's
choices and the card. A layer's `label` is its own name, written `<rule>: <layer>`
(`RULE_SEPARATOR`) where more than one rule is drawn, and its `caption` is the same with the
rule's title in place of its name. On this repository the Layer filter's value is
`site-fsd-layers: widgets` and the reader is shown `FSD architecture: widgets`. A one-rule
project keeps bare names.

**Colours.** A layer's colour is a theme tone chosen by its position in its own rule, so each
rule's layers are told apart and the legend, grouped per rule, says which rule a tone belongs to.
`LAYER_TONES` has six tones, so the six Feature-Sliced layers each have one: purple, indigo,
green, yellow, red and the portal's own cyan (`--bl-c-cyan-1`, defined in
`shared/theme-tokens/tones.css`). The sixth is not VitePress's brand colour: `--vp-c-brand-1` is
`--vp-c-indigo-1` in the VitePress release the scaffold pins, so it would draw the second layer and the sixth alike, and
the next candidate, `--vp-c-sponsor`, measured 2.78:1 in the dark theme on a tinted box, under
the 3:1 the look spec holds. A node is drawn in its layer's tone: a border in it over a tint of
it at `LAYER_FILL_SHARE` (0.16), leaf or box alike (BDL-078). A node in no layer takes
`UNLAYERED_TONE`, VitePress's `--vp-c-text-2`, and is named `UNLAYERED_NAME` ("no layer");
`hasUnlayeredNode(nodes, layers)` tells the viewer whether any node is drawn that way, in which
case the legend adds a "no layer" item (`data-legend-unlayered`), headed `Layers:` when it is the
only one. The viewer asks it about every node but the box that holds everything, which is the
project's frame whatever its layer.

**The legend** groups the layers per rule (`[data-legend-rule]`) under
`<title or rule> (top → bottom):` where two or more rules are drawn. One rule, or a file that
names one order, is one group under `<title> (top → bottom):` when the rule is titled, else
`Layers (top → bottom):`. Each `[data-legend-layer]` item carries the layer's label.

**Lanes** (`lanesOf`). ELK lays the graph out top to bottom and pins a node with a partition into
that partition's band. A rank says where a layer stands only beside the other layers of its own
rule, so a node's lane is its layer's rank among the siblings of one rule. Where a box holds
parts of more than one rule, the rule that places most of them gives the lanes, the first in the
layers' order on a tie, and the others have none. A file that names one order gives every node
its rank, as before.

**Layer boxes** (`layerBoxesOf`). A rule whose scope is a box other than the project's frame
draws one box per layer inside its scope, each holding the scope's own parts that the rule places
in that layer. A layer box is no node of the graph: no `part_of` edge names it and the data file
does not list it, so it has no card, no filter value and no page, and a tap on it selects
nothing. Its id is `layer:<rule>/<layer>`, made unique against the node ids. A rule scoped to the
frame itself draws no box, because boxes there would turn the overview of the whole project into
a map of its layers. A part the scope holds that its rule does not place stays directly in the
scope. On this repository `vitepress-site` holds six layer boxes, app, pages, widgets, features,
entities and shared, stacked top to bottom; `architecture-layers`, whose derived scope is the
frame `beadloom`, draws none.

## Public API

- `layersOf(nodes, declared, rules)` returns
  `[{ key, rule, ruleTitle, rank, name, label, caption, tag, tone }]`: every rule's layers, the
  rules in the file's order and each top to bottom. `rules` is the file's `layer_rules`;
  `declared` its `layers`, read only when `rules` names none (`rule` is then `null`).
- `layerRulesOf(layers)` returns `[{ rule, title, layers }]`; `declaredRulesOf(rules)` the
  file's rules that have a name and at least one layer; `ruleCaptionOf(layer)` the rule's title,
  else its name.
- `layerOfNode(node, layers)` — the layer of the rule that places the node, at its rank, where
  the layers are a rule's, else the layer of its `layer_rank`; `ownsLayer(node, layers)` —
  whether the node carries that layer's tag itself rather than inheriting it through `part_of`.
- `layerToneOf(node, layers)`, `LAYER_TONES`, `UNLAYERED_TONE` (`text2`), `UNLAYERED_NAME`,
  `LAYER_FILL_SHARE`, `RULE_SEPARATOR` (`": "`), `hasUnlayeredNode(nodes, layers)`.
- `lanesOf(nodes, { parents, layers, layerBoxes })` returns `Map(id => rank)`.
- `layerBoxesOf(nodes, parents, layers, rules)` returns `{ boxes, parents }`: the boxes
  `[{ id, label, rule, rank, tone, scope }]` and the containment the canvas draws, with each
  placed part moved into its layer's box and each layer box in its scope.
- `LayerLegend` (Vue component): props `layers` and `unlayered` (Boolean); each sample is a
  swatch drawn as the canvas draws the layer, a border over a tint at `LAYER_FILL_SHARE`.

## Depends on

- `site-shared`, for the theme variables the legend swatches use.

## Tests

`src/beadloom/site_scaffold/e2e/layers.spec.js`: the legend names the declared layers top to
bottom; the Layer filter offers them and keeps the nodes in the chosen layer; the card names a
node's layer, own or inherited; a file that declares no layer names falls back to the nodes'
tokens; each layer has a colour of its own within its rule, six tones for six layers; every node
is drawn in its layer's colour as the legend draws it; the legend names "no layer" exactly when a
node is in none. Since BDL-080: the legend groups the layers per rule under the rule's title or
name; the Layer filter offers each layer by its rule's title and carries the rule's name in its
value; the card names the rule that places a node; a rule's title names it in the legend, the
filter and the card while the URL keeps its name; a file of one titled rule heads its legend with
the title; lanes partition the siblings of one rule, at the top and inside a scope by its layer
boxes; and a file of one layer rule is drawn the same with every rule's keys as without them.
The layer boxes are held by `layer-boxes.spec.js` on the viewer.
