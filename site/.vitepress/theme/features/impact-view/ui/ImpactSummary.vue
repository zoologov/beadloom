<script setup>
// beadloom:component=site-impact-view
// The impact mode's summary in the viewer's panel.
//
// It states first that this is the graph's view, then the count, the rings by
// distance in their colours, the domains and services, the layer boundaries
// crossed and the risky nodes, and last the two terminal commands that give
// the code-level answer. A click on a node in it asks the viewer to select it.

import { shellQuote } from "../../../shared/lib/index.js";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { CopyCommand } from "../../../shared/ui/index.js";
import { RING_TONES, ringOf } from "../model/rings.js";

defineProps({
  summary: { type: Object, required: true },
  source: { type: String, default: "" },
});
const emit = defineEmits(["select"]);

function swatch(distance) {
  return { background: `var(${TOKEN_VARIABLES[RING_TONES[ringOf(distance)]]})` };
}
</script>

<template>
  <section class="bl-impact" data-testid="impact-summary" aria-label="Impact">
    <h3>Impact of {{ summary.focus }}</h3>
    <p class="bl-impact-statement">
      This is the graph view — not a reading of the code. It follows the
      <code>depends_on</code>, <code>uses</code> and <code>consumes</code> edges the index holds,
      which come from imports and declarations.
    </p>

    <p class="bl-impact-count">
      <strong data-testid="impact-count">{{ summary.affected.length }}</strong>
      {{ summary.affected.length === 1 ? "node depends" : "nodes depend" }} on it.
    </p>
    <ul v-if="summary.byDistance.length" class="bl-impact-rings">
      <li v-for="ring in summary.byDistance" :key="ring.distance">
        <span class="bl-impact-swatch" :style="swatch(ring.distance)" />
        distance {{ ring.distance }}: {{ ring.ids.length }}
      </li>
    </ul>

    <dl>
      <dt>Domains</dt>
      <dd>{{ summary.domains.join(", ") || "none" }}</dd>
      <dt>Services</dt>
      <dd>{{ summary.services.join(", ") || "none" }}</dd>
      <dt>Layer boundaries crossed</dt>
      <dd>
        <template v-if="!summary.boundaries.length">none</template>
        <span v-for="b in summary.boundaries" v-else :key="`${b.fromRank}->${b.toRank}`" class="bl-impact-boundary">
          {{ b.from }} → {{ b.to }} ({{ b.count }})
        </span>
      </dd>
    </dl>

    <h4>Risks</h4>
    <p v-if="!summary.risky.length" class="bl-impact-none">none</p>
    <ul v-else data-testid="impact-risks" class="bl-impact-risks">
      <li v-for="entry in summary.risky" :key="entry.id" :data-risk-node="entry.id">
        <button type="button" class="bl-impact-link" @click="emit('select', entry.id)">{{ entry.id }}</button>
        <span class="bl-impact-risk">{{ entry.risks.join(", ") }}</span>
      </li>
    </ul>

    <h4>The code-level answer</h4>
    <CopyCommand :command="`beadloom why ${shellQuote(summary.focus)}`" />
    <CopyCommand v-if="source" :command="`beadloom impact ${shellQuote(source)}`" />
  </section>
</template>

<style scoped>
.bl-impact {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--vp-c-divider);
  font-size: 13px;
}
.bl-impact h3 {
  margin: 0 28px 6px 0;
  font-size: 15px;
}
.bl-impact h4 {
  margin: 12px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-impact p {
  margin: 4px 0;
}
.bl-impact-statement {
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--vp-c-bg-alt);
  color: var(--vp-c-text-2);
}
.bl-impact dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 8px 0 0;
}
.bl-impact dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-impact dd {
  margin: 0;
  min-width: 0;
  word-break: break-word;
}
.bl-impact ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-impact-rings {
  list-style: none;
  padding-left: 0 !important;
}
.bl-impact-swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 6px;
  border-radius: 50%;
  vertical-align: -2px;
}
.bl-impact-boundary {
  display: block;
}
.bl-impact-risk {
  margin-left: 6px;
  color: var(--vp-c-warning-1);
}
.bl-impact-link {
  padding: 0;
  border: none;
  background: none;
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  color: var(--vp-c-brand-1);
  cursor: pointer;
}
.bl-impact-none {
  color: var(--vp-c-text-3);
  font-style: italic;
}
</style>
