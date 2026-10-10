<script setup>
// beadloom:component=site-impact-view
// The impact mode's summary in the viewer's panel.
//
// It states first that this is the graph's view, then the count, the rings by
// distance in their colours, what the walk crossed and the risky nodes, and
// last the terminal commands for the answer beyond the graph. What the walk
// crossed depends on the walk the summary reads: in the architecture, the
// domains, services and layer boundaries (`impact.js`); on the landscape, the
// contracts, their protocols and the broken ones (`contractImpact.js`). The
// commands are those that take what was selected: a node's ref and its source
// in the architecture, and a service's ref on the landscape, where `impact`,
// which takes a path, has nothing to take. A click on a node in it asks the
// viewer to select it.

import { computed } from "vue";
import { shellQuote } from "../../../shared/lib/index.js";
import { RING_TONES, TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { CopyCommand } from "../../../shared/ui/index.js";
import { CONTRACT_WALK } from "../lib/contractImpact.js";
import { ringOf } from "../model/rings.js";

const props = defineProps({
  summary: { type: Object, required: true },
  source: { type: String, default: "" },
});
const emit = defineEmits(["select"]);

const overContracts = computed(() => props.summary.walk === CONTRACT_WALK);

const commands = computed(() => {
  const ref = shellQuote(props.summary.focus);
  if (overContracts.value) return [`beadloom why ${ref}`, `beadloom ctx ${ref}`];
  const commands = [`beadloom why ${ref}`];
  if (props.source) commands.push(`beadloom impact ${shellQuote(props.source)}`);
  return commands;
});

/** The words after the count of what the walk reached. */
function reachLine(count) {
  const one = count === 1;
  if (overContracts.value) {
    return one ? "service is reached through contracts." : "services are reached through contracts.";
  }
  return one ? "node depends on it." : "nodes depend on it.";
}

function swatch(distance) {
  return { background: `var(${TOKEN_VARIABLES[RING_TONES[ringOf(distance)]]})` };
}
</script>

<template>
  <section class="bl-impact" data-testid="impact-summary" aria-label="Impact">
    <h3>Impact of {{ summary.focus }}</h3>
    <p v-if="overContracts" class="bl-impact-statement">
      This is the graph view — not a reading of the code. It follows the contracts the landscape
      records, from each producer to its consumers, whatever the protocol: a service that consumes
      what a changed service produces is reached, and so are its own consumers.
    </p>
    <p v-else class="bl-impact-statement">
      This is the graph view — not a reading of the code. It follows the
      <code>depends_on</code>, <code>uses</code> and <code>consumes</code> edges the index holds,
      which come from imports and declarations.
    </p>

    <p class="bl-impact-count">
      <strong data-testid="impact-count">{{ summary.affected.length }}</strong>
      {{ reachLine(summary.affected.length) }}
    </p>
    <ul v-if="summary.byDistance.length" class="bl-impact-rings">
      <li v-for="ring in summary.byDistance" :key="ring.distance">
        <span class="bl-impact-swatch" :style="swatch(ring.distance)" />
        distance {{ ring.distance }}: {{ ring.ids.length }}
      </li>
    </ul>

    <dl v-if="overContracts">
      <dt>Contracts crossed</dt>
      <dd>
        <strong data-testid="impact-contract-count">{{ summary.contracts.length }}</strong>
        <template v-if="summary.contracts.length">: {{ summary.contracts.join(", ") }}</template>
      </dd>
      <dt>Protocols</dt>
      <dd>{{ summary.protocols.join(", ") || "none" }}</dd>
      <dt>Broken on the path</dt>
      <dd>
        <template v-if="!summary.broken.length">none</template>
        <code v-for="key in summary.broken" v-else :key="key" class="bl-impact-broken" :data-broken-contract="key">{{ key }}</code>
      </dd>
    </dl>
    <dl v-else>
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

    <h4>{{ overContracts ? "In the terminal" : "The code-level answer" }}</h4>
    <CopyCommand v-for="command in commands" :key="command" :command="command" />
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
.bl-impact-boundary,
.bl-impact-broken {
  display: block;
}
.bl-impact-broken {
  width: fit-content;
  color: var(--vp-c-danger-1);
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
