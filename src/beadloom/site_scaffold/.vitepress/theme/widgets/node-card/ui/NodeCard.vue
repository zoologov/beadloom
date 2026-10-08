<script setup>
// beadloom:component=site-node-card
// A node's card: everything the data file says about one node.
//
// Identity (kind, summary, lifecycle, tags), the layer it is in, the rule that
// places it there where the data file names every layer rule, and whether the
// tag is its own or inherited, its source linked to the address the data
// file gives (the generator decides it per forge, and gives none for a host it
// does not recognise, so the card knows no forge), its
// docs each with its freshness, its bound tests, its public symbols, its edges
// by kind and direction, its rule findings, its activity and its debt, then the
// node's page and the `ctx` and `why` commands to copy. A box's card says as well
// what it holds and where its edges to the outside go: how many to and from each
// node its lines on the map join it to.
//
// Every value comes from the data file. A field the file holds nothing for says
// "none"; a field a version 1 file does not carry at all says "not recorded",
// because the two are different answers. A click on an edge's other end asks the
// viewer to select that node.

import { computed } from "vue";
import { withBase } from "vitepress";
import { boxEdgesOf, edgeGroupsOf } from "../../../entities/graph-edge/index.js";
import { layerOfNode, ownsLayer } from "../../../entities/layer/index.js";
import { shellQuote } from "../../../shared/lib/index.js";
import { CopyCommand } from "../../../shared/ui/index.js";

const props = defineProps({
  node: { type: Object, required: true },
  edges: { type: Array, default: () => [] },
  layers: { type: Array, default: () => [] },
  // Each node's box, `{ id: parent | null }`: a box's card says what it holds.
  parents: { type: Object, default: null },
});
const emit = defineEmits(["select", "close"]);

const NOT_RECORDED = "not recorded";
const NONE = "none";

const layer = computed(() => layerOfNode(props.node, props.layers));
// Where the layer comes from: the rule that places the node, where the file names it, and whether the tag is the node's own.
const layerOrigin = computed(() => {
  if (!layer.value) return "";
  const origin = ownsLayer(props.node, props.layers) ? "its own tag" : "inherited through part_of";
  return layer.value.rule ? `rule ${layer.value.rule}, ${origin}` : origin;
});

const sourceUrl = computed(() => props.node.source_url || "");

// A doc's page, when the site published one: its served link ends with the doc's path.
const docLinkOf = computed(() => {
  const links = props.node.doc_links || [];
  return (path) => links.find((link) => link.endsWith(`/${path.replace(/\.md$/, ".html")}`)) || "";
});

const edgeGroups = computed(() => edgeGroupsOf(props.node.id, props.edges));
// What a box holds and where its edges go, or null for a node that holds nothing.
const contents = computed(() => (props.parents ? boxEdgesOf(props.node.id, props.edges, props.parents) : null));
const sumOf = (entries) => entries.reduce((sum, entry) => sum + entry.count, 0);

// The activity line: changed lines in 30 days and the level, which is relative
// to the project. A node with no change in
// its window says so in words, not as a low count. A data file written before
// lines were counted carries commits only, and is said in commits. One line or
// one commit is said in the singular.
const NO_CHANGE = new Map([
  ["quiet", "no change in 30 days"],
  ["dormant", "no change in 90 days"],
]);
/** `count` followed by `one` when it is 1, and by `many` otherwise. */
const countOf = (count, one, many) => `${count} ${count === 1 ? one : many}`;
const activityLine = computed(() => {
  const activity = props.node.activity;
  if (!activity) return NOT_RECORDED;
  const level = activity.level || "";
  let said = NO_CHANGE.get(level);
  if (said === undefined) {
    said = activity.lines_30d === undefined
      ? `${countOf(activity.commits_30d ?? 0, "commit", "commits")} in 30 days`
      : `${countOf(activity.lines_30d, "line", "lines")} changed in 30 days`;
  }
  return level ? `${said}, ${level}` : said;
});

const placements = computed(() =>
  Object.entries(props.node.tests?.placement || {}).sort(([a], [b]) => a.localeCompare(b))
);
</script>

<template>
  <article class="bl-card" data-testid="node-card" :aria-label="`Node ${node.id}`">
    <button type="button" class="bl-card-close" aria-label="Close the card" @click="emit('close')">
      ×
    </button>
    <h3>{{ node.id }}</h3>
    <p class="bl-card-summary" data-card-field="summary">{{ node.summary || NONE }}</p>

    <dl>
      <dt>Kind</dt>
      <dd data-card-field="kind">{{ node.kind || NONE }}</dd>
      <dt>Lifecycle</dt>
      <dd data-card-field="lifecycle">{{ node.lifecycle || (node.lifecycle === "" ? NONE : NOT_RECORDED) }}</dd>
      <dt>Tags</dt>
      <dd data-card-field="tags">
        <template v-if="node.tags === undefined">{{ NOT_RECORDED }}</template>
        <template v-else-if="!node.tags.length">{{ NONE }}</template>
        <code v-for="tag in node.tags" v-else :key="tag" class="bl-card-tag">{{ tag }}</code>
      </dd>
      <dt>Layer</dt>
      <dd data-card-field="layer">
        <template v-if="layer">{{ layer.name }} <span class="bl-card-note">({{ layerOrigin }})</span></template>
        <template v-else>{{ NONE }}</template>
      </dd>
      <dt>Source</dt>
      <dd data-card-field="source">
        <template v-if="!node.source">{{ node.source === undefined ? NOT_RECORDED : NONE }}</template>
        <a v-else-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener"><code>{{ node.source }}</code></a>
        <code v-else>{{ node.source }}</code>
      </dd>
      <dt>Activity</dt>
      <dd data-card-field="activity">{{ activityLine }}</dd>
      <dt>Debt</dt>
      <dd data-card-field="debt">
        <template v-if="node.debt === undefined">{{ NOT_RECORDED }}</template>
        <template v-else-if="!node.debt">{{ NONE }}</template>
        <template v-else>
          {{ node.debt.score }}<template v-if="(node.debt.reasons || []).length"> ({{ node.debt.reasons.join(", ") }})</template>
        </template>
      </dd>
    </dl>

    <section data-card-field="docs">
      <h4>Docs</h4>
      <p v-if="node.docs === undefined" class="bl-card-none">{{ node.doc_status || NOT_RECORDED }}</p>
      <p v-else-if="!node.docs.length" class="bl-card-none">{{ NONE }}</p>
      <ul v-else>
        <li v-for="doc in node.docs" :key="doc.path">
          <a v-if="docLinkOf(doc.path)" :href="withBase(docLinkOf(doc.path))">{{ doc.path }}</a>
          <span v-else>{{ doc.path }}</span>
          <span class="bl-card-status" :class="{ 'bl-card-warn': doc.status !== 'ok' }">{{ doc.status }}</span>
        </li>
      </ul>
    </section>

    <section data-card-field="tests">
      <h4>Bound tests</h4>
      <p v-if="!node.tests" class="bl-card-none">{{ NOT_RECORDED }}</p>
      <template v-else>
        <p class="bl-card-line" :class="{ 'bl-card-warn': node.tests.count === 0 }">
          {{ node.tests.count }} tests in {{ node.tests.file_count ?? node.tests.files.length }} files
        </p>
        <p v-if="placements.length" class="bl-card-line">
          <span v-for="[placement, count] in placements" :key="placement" class="bl-card-chip">{{ placement }}: {{ count }}</span>
        </p>
        <details v-if="node.tests.files.length">
          <summary>{{ node.tests.files.length }} files bound to this node itself</summary>
          <ul>
            <li v-for="file in node.tests.files" :key="file"><code>{{ file }}</code></li>
          </ul>
        </details>
      </template>
    </section>

    <section data-card-field="symbols">
      <h4>Public symbols</h4>
      <p v-if="!node.public_symbols" class="bl-card-none">{{ node.symbols ?? NOT_RECORDED }}</p>
      <p v-else-if="!node.public_symbols.names.length" class="bl-card-none">{{ NONE }}</p>
      <details v-else>
        <summary>
          {{ node.public_symbols.names.length + (node.public_symbols.omitted || 0) }} names<template v-if="node.public_symbols.omitted">, the first {{ node.public_symbols.names.length }} shown</template>
        </summary>
        <p class="bl-card-symbols">
          <code v-for="name in node.public_symbols.names" :key="name">{{ name }}</code>
        </p>
      </details>
    </section>

    <section v-if="contents" data-card-field="contents">
      <h4>Inside</h4>
      <p class="bl-card-line" :data-contents-inside="contents.inside">
        {{ contents.inside }} {{ contents.inside === 1 ? "node" : "nodes" }}
      </p>
      <h5>{{ sumOf(contents.out) }} {{ sumOf(contents.out) === 1 ? "edge" : "edges" }} out</h5>
      <p v-if="!contents.out.length" class="bl-card-none">{{ NONE }}</p>
      <ul v-else>
        <li v-for="entry in contents.out" :key="entry.id" :data-contents-out="entry.id" :data-count="entry.count">
          to <code>{{ entry.id }}</code>: {{ entry.count }}
        </li>
      </ul>
      <h5>{{ sumOf(contents.in) }} {{ sumOf(contents.in) === 1 ? "edge" : "edges" }} in</h5>
      <p v-if="!contents.in.length" class="bl-card-none">{{ NONE }}</p>
      <ul v-else>
        <li v-for="entry in contents.in" :key="entry.id" :data-contents-in="entry.id" :data-count="entry.count">
          from <code>{{ entry.id }}</code>: {{ entry.count }}
        </li>
      </ul>
    </section>

    <section data-card-field="edges">
      <h4>Edges</h4>
      <p v-if="!edgeGroups.length" class="bl-card-none">{{ NONE }}</p>
      <template v-for="group in edgeGroups" :key="`${group.kind}:${group.direction}`">
        <h5>{{ group.title }}</h5>
        <ul>
          <li v-for="target in group.targets" :key="target.id">
            <button
              type="button"
              class="bl-card-link"
              :class="{ 'bl-card-violation': target.violation }"
              :data-edge-kind="group.kind"
              :data-edge-direction="group.direction"
              :data-edge-target="target.id"
              :title="target.violation ? 'Against the declared layers' : ''"
              @click="emit('select', target.id)"
            >
              {{ target.id }}
            </button>
          </li>
        </ul>
      </template>
    </section>

    <section data-card-field="findings">
      <h4>Rule findings</h4>
      <p v-if="node.findings === undefined" class="bl-card-none">
        {{ node.lint_clean === undefined ? NOT_RECORDED : node.lint_clean ? NONE : "violation" }}
      </p>
      <p v-else-if="!node.findings.length" class="bl-card-none">{{ NONE }}</p>
      <ul v-else>
        <li v-for="(finding, index) in node.findings" :key="index">
          <code>{{ finding.rule }}</code>
          <span class="bl-card-severity" :class="{ 'bl-card-warn': finding.severity === 'error' }">{{ finding.severity }}</span>
          {{ finding.message }}
        </li>
      </ul>
    </section>

    <section data-card-field="page">
      <h4>Page</h4>
      <p v-if="node.url"><a :href="withBase(node.url)">Open the node's page →</a></p>
      <p v-else class="bl-card-none">{{ NONE }}</p>
    </section>

    <section data-card-field="commands">
      <h4>In the terminal</h4>
      <CopyCommand :command="`beadloom ctx ${shellQuote(node.id)}`" />
      <CopyCommand :command="`beadloom why ${shellQuote(node.id)}`" />
    </section>
  </article>
</template>

<style scoped>
.bl-card {
  position: relative;
  font-size: 13px;
}
.bl-card h3 {
  margin: 0 28px 6px 0;
  font-size: 15px;
  word-break: break-word;
}
.bl-card h4 {
  margin: 14px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-card h5 {
  margin: 8px 0 2px;
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-card dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 10px 0 0;
}
.bl-card dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-card dd {
  margin: 0;
  min-width: 0;
  word-break: break-word;
}
.bl-card ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-card p {
  margin: 4px 0;
}
.bl-card code {
  font-size: 12px;
}
.bl-card-summary {
  color: var(--vp-c-text-2);
}
.bl-card-note {
  color: var(--vp-c-text-3);
}
.bl-card-tag,
.bl-card-chip {
  display: inline-block;
  margin: 0 4px 2px 0;
}
.bl-card-chip {
  padding: 0 6px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  font-size: 12px;
}
.bl-card-status,
.bl-card-severity {
  margin-left: 6px;
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-card-symbols {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
}
.bl-card details summary {
  cursor: pointer;
  color: var(--vp-c-text-2);
}
.bl-card-close {
  position: absolute;
  top: -4px;
  right: 0;
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: var(--vp-c-text-2);
}
.bl-card-link {
  padding: 0;
  border: none;
  background: none;
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  color: var(--vp-c-brand-1);
  cursor: pointer;
  text-align: left;
}
.bl-card-link:hover {
  text-decoration: underline;
}
.bl-card-violation {
  color: var(--vp-c-danger-1);
}
.bl-card-none {
  color: var(--vp-c-text-3);
  font-style: italic;
}
.bl-card-warn {
  color: var(--vp-c-warning-1);
  font-weight: 700;
}
</style>
