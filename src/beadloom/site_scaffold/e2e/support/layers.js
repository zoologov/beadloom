// The browser tests' own reading of the layers: which layer a node is in, and the boxes a scoped rule draws.
//
// Written again here from the data file's declaration rather than imported from
// the viewer, so a case that asks which layer a node is in, or which box holds
// it, gets the product's rule and not the viewer's answer to it:
//
// - A file that carries `layer_rules` names a layer by its rule and rank: a node
//   is in the layer of `layer_rule` at `layer_rule_rank`. A file without them is
//   read as before: a node is in the declared layer of its `layer_rank`.
// - A layer's name says its rule's (`rule: name`) where the file declares more
//   than one rule; with one rule, a layer is named as before. That is its
//   `label`, the value the Layer filter and the URL carry: the rule's NAME, its
//   identifier. What a reader is shown, its `caption`, says the rule's `title`
//   instead where the rule declares one (`title: name`), and the name where not.
// - A rule whose scope is a box inside the project's frame draws one box per
//   layer in that box: each holds the scope's own parts in that layer, and every
//   other part stays where it is. A rule scoped to the frame itself, the box that
//   holds everything, draws its layers as lanes, as before.

/** What joins a rule's name and a layer's where more than one rule is drawn. */
export const RULE_SEPARATOR = ": ";

/** The id the viewer gives the box of `layer` of `rule`, where no node of the file has that id. */
export const layerBoxId = (rule, layer) => `layer:${rule}/${layer}`;

/** The layer rules the file declares, in its order, each with at least one layer. */
export function layerRulesOf(data) {
  const rules = Array.isArray(data.layer_rules) ? data.layer_rules : [];
  return rules.filter((rule) => rule?.name && (rule.layers || []).some((layer) => typeof layer?.rank === "number"));
}

/** What a reader is shown a rule by: its declared title, else its name. */
export const ruleCaptionOf = (rule) => (typeof rule?.title === "string" && rule.title) || rule?.name || "";

/**
 * The layers, `[{ rule, title, rank, name, label, caption, tag }]`: each rule's
 * top to bottom, or, for a file without rules, its declared `layers` with `rule`
 * null. `title` is the rule's declared title, "" where it has none.
 */
export function layersOfData(data) {
  const rules = layerRulesOf(data);
  if (!rules.length) {
    return [...(data.layers || [])]
      .filter((layer) => typeof layer?.rank === "number")
      .sort((a, b) => a.rank - b.rank)
      .map((layer) => ({ rule: null, title: "", rank: layer.rank, name: layer.name, label: layer.name, caption: layer.name, tag: layer.tag }));
  }
  return rules.flatMap((rule) =>
    [...rule.layers]
      .filter((layer) => typeof layer?.rank === "number")
      .sort((a, b) => a.rank - b.rank)
      .map((layer) => ({
        rule: rule.name,
        title: typeof rule.title === "string" ? rule.title : "",
        rank: layer.rank,
        name: layer.name,
        label: rules.length > 1 ? `${rule.name}${RULE_SEPARATOR}${layer.name}` : layer.name,
        caption: rules.length > 1 ? `${ruleCaptionOf(rule)}${RULE_SEPARATOR}${layer.name}` : layer.name,
        tag: layer.tag,
      }))
  );
}

/** The layer `node` is in, or null: by its rule and rank where the file carries rules, else by its rank. */
export function layerOfNode(node, data, layers = layersOfData(data)) {
  if (layerRulesOf(data).length) {
    return layers.find((layer) => layer.rule === node.layer_rule && layer.rank === node.layer_rule_rank) || null;
  }
  return layers.find((layer) => layer.rank === node.layer_rank) || null;
}

/** `data` without the keys every rule is drawn from: a file as the viewer read it before they were written. */
export function withoutLayerRules(data) {
  const { layer_rules: _rules, ...rest } = data;
  return {
    ...rest,
    nodes: data.nodes.map(({ layer_rule: _rule, layer_rule_rank: _rank, ...node }) => node),
  };
}

/** `data` with every layer rule titled by `titleOf(rule)`, or with no title where it answers null. */
export function withRuleTitles(data, titleOf) {
  return {
    ...data,
    layer_rules: (data.layer_rules || []).map(({ title: _title, ...rule }) => {
      const title = titleOf(rule);
      return title === null ? rule : { ...rule, title };
    }),
  };
}

/** Each node's parent in the file (a root that is its own parent has none). */
export function fileParentMap(data) {
  const ids = new Set(data.nodes.map((n) => n.id));
  const parents = {};
  for (const n of data.nodes) {
    parents[n.id] = n.parent && n.parent !== n.id && ids.has(n.parent) ? n.parent : null;
  }
  return parents;
}

/**
 * The boxes the scoped rules draw, `[{ id, rule, rank, name, scope, members }]`:
 * one per layer that holds a part of its rule's scope, where the scope is a box
 * and not the one root that holds everything; `members` are the scope's own
 * parts in that layer, sorted.
 */
export function layerBoxesOf(data) {
  const parents = fileParentMap(data);
  const boxes = new Set(Object.values(parents).filter(Boolean));
  const roots = Object.keys(parents).filter((id) => !parents[id]);
  const frame = roots.length === 1 && boxes.has(roots[0]) ? roots[0] : null;
  const layers = layersOfData(data);
  const found = [];
  for (const rule of layerRulesOf(data)) {
    if (!rule.scope || rule.scope === frame || !boxes.has(rule.scope)) continue;
    for (const layer of layers.filter((l) => l.rule === rule.name)) {
      const members = data.nodes
        .filter((node) => parents[node.id] === rule.scope && layerOfNode(node, data, layers) === layer)
        .map((node) => node.id)
        .sort();
      if (members.length) {
        found.push({ id: layerBoxId(rule.name, layer.name), rule: rule.name, rank: layer.rank, name: layer.name, scope: rule.scope, members });
      }
    }
  }
  return found;
}

/**
 * Each drawn node's box: the file's parent, or the layer box a scoped rule draws
 * around the node, and each layer box's scope.
 */
export function drawnParentMap(data) {
  const parents = fileParentMap(data);
  for (const box of layerBoxesOf(data)) {
    parents[box.id] = box.scope;
    for (const member of box.members) parents[member] = box.id;
  }
  return parents;
}
