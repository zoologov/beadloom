<script setup>
// beadloom:component=site-landscape-page
// The landscape card: a service, its health, its page, and every contract it
// produces or consumes.
//
// Each contract shows its verdict, its producers and consumers (a click on one
// selects it), and, when it is declared in a protocol the reconciler reads, the
// protocol, its routing and its surface: the GraphQL fields each side names, or
// the AMQP message body. A surface that was not declared says "undeclared",
// never an invented field, and a contract with no such protocol is shown as a
// plain dependency, with no protocol line at all rather than "unknown". This
// card holds what the old map's edge card showed, so a contract is reached
// from either of its ends.

import { computed } from "vue";
import { withBase } from "vitepress";
import { healthOf, isDeclaredContract, takesPart } from "../../../entities/landscape-data/index.js";

const props = defineProps({
  node: { type: Object, required: true },
  contracts: { type: Array, default: () => [] },
});
const emit = defineEmits(["select", "close"]);

const mine = computed(() =>
  props.contracts
    .filter((contract) => takesPart(contract, props.node.id))
    .sort((a, b) => a.contract_key.localeCompare(b.contract_key))
);

const isEmpty = (value) => !value || (typeof value === "object" && Object.keys(value).length === 0);

/** `[{ name, type }]` of a GraphQL field surface, sorted by name. */
function fieldsOf(surface) {
  if (isEmpty(surface)) return [];
  return Object.keys(surface)
    .sort()
    .map((name) => ({ name, type: surface[name]?.type || "unknown" }));
}

/** `[{ name, type }]` of an AMQP body's properties, sorted by name. */
function propertiesOf(body) {
  return fieldsOf(body?.properties);
}

function verdictOf(contract) {
  return String(contract.verdict || "").toUpperCase();
}
</script>

<template>
  <article class="bl-lcard" data-testid="landscape-card">
    <button type="button" class="bl-lcard-close" aria-label="Close the card" @click="emit('close')">
      ×
    </button>
    <h3>{{ node.id }}</h3>
    <dl>
      <dt>Kind</dt>
      <dd>{{ node.kind || "unknown" }}</dd>
      <dt>Health</dt>
      <dd :class="`bl-v-${node.health}`">{{ node.health }}</dd>
      <dt>Contracts</dt>
      <dd>{{ mine.length }}</dd>
    </dl>
    <p v-if="node.url"><a :href="withBase(node.url)">Open the service's page →</a></p>

    <section
      v-for="contract in mine"
      :key="contract.contract_key"
      class="bl-lcard-contract"
      :data-contract="contract.contract_key"
    >
      <template v-if="isDeclaredContract(contract)">
        <h4>{{ contract.name || contract.contract_key }}</h4>
        <dl>
          <dt>Protocol</dt>
          <dd>{{ contract.protocol }}</dd>
          <dt>Verdict</dt>
          <dd :class="`bl-v-${healthOf(contract.verdict)}`">{{ verdictOf(contract) }}</dd>
          <template v-if="contract.protocol === 'amqp'">
            <dt>Routing</dt>
            <dd>
              {{ contract.routing?.exchange || "*" }} / {{ contract.routing?.routing_key || "*" }}
              ({{ contract.routing?.message_type || "?" }})
            </dd>
          </template>
          <template v-else>
            <dt>Schema</dt>
            <dd>{{ contract.routing?.schema || contract.name }}</dd>
          </template>
        </dl>
        <template v-if="contract.protocol === 'graphql'">
          <h5>Exposed fields (producer)</h5>
          <ul v-if="fieldsOf(contract.fields?.exposed).length">
            <li v-for="f in fieldsOf(contract.fields?.exposed)" :key="f.name">
              <code>{{ f.name }}</code>: {{ f.type }}
            </li>
          </ul>
          <p v-else class="bl-lcard-undeclared">undeclared</p>
          <h5>Referenced fields (consumer)</h5>
          <ul v-if="fieldsOf(contract.fields?.referenced).length">
            <li v-for="f in fieldsOf(contract.fields?.referenced)" :key="f.name">
              <code>{{ f.name }}</code>: {{ f.type }}
            </li>
          </ul>
          <p v-else class="bl-lcard-undeclared">undeclared</p>
        </template>
        <template v-else>
          <h5>Body (producer)</h5>
          <ul v-if="propertiesOf(contract.body?.exposed).length">
            <li v-for="f in propertiesOf(contract.body?.exposed)" :key="f.name">
              <code>{{ f.name }}</code>: {{ f.type }}
            </li>
          </ul>
          <p v-else class="bl-lcard-undeclared">undeclared</p>
        </template>
        <template v-if="(contract.missing || []).length">
          <h5 class="bl-v-broken">Breaking</h5>
          <ul>
            <li v-for="m in contract.missing" :key="m"><code>{{ m }}</code></li>
          </ul>
        </template>
      </template>

      <template v-else>
        <h4>Dependency: {{ contract.name || contract.contract_key }}</h4>
        <dl>
          <dt>Verdict</dt>
          <dd :class="`bl-v-${healthOf(contract.verdict)}`">{{ verdictOf(contract) }}</dd>
        </dl>
        <p class="bl-lcard-undeclared">
          A plain dependency, not a declared contract — no protocol surface.
        </p>
      </template>

      <dl>
        <dt>Producers</dt>
        <dd>
          <button
            v-for="id in contract.producers || []"
            :key="id"
            type="button"
            class="bl-lcard-link"
            :disabled="id === node.id"
            @click="emit('select', id)"
          >
            {{ id }}
          </button>
          <span v-if="!(contract.producers || []).length">none</span>
        </dd>
        <dt>Consumers</dt>
        <dd>
          <button
            v-for="id in contract.consumers || []"
            :key="id"
            type="button"
            class="bl-lcard-link"
            :disabled="id === node.id"
            @click="emit('select', id)"
          >
            {{ id }}
          </button>
          <span v-if="!(contract.consumers || []).length">none</span>
        </dd>
      </dl>
    </section>
  </article>
</template>

<style scoped>
.bl-lcard {
  position: relative;
  font-size: 13px;
}
.bl-lcard h3 {
  margin: 0 28px 8px 0;
  font-size: 15px;
  word-break: break-word;
}
.bl-lcard h4 {
  margin: 0 0 6px;
  font-size: 13px;
}
.bl-lcard h5 {
  margin: 10px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-lcard dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 0 0 6px;
}
.bl-lcard dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-lcard dd {
  margin: 0;
}
.bl-lcard ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-lcard-contract {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--vp-c-divider);
}
.bl-lcard-close {
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
.bl-lcard-link {
  margin: 0 6px 2px 0;
  padding: 0;
  border: none;
  background: none;
  color: var(--vp-c-brand-1);
  font-size: 13px;
  cursor: pointer;
}
.bl-lcard-link:disabled {
  color: var(--vp-c-text-1);
  cursor: default;
}
.bl-lcard-undeclared {
  color: var(--vp-c-text-3);
  font-style: italic;
}
.bl-v-broken {
  color: var(--vp-c-danger-1);
  font-weight: 700;
}
.bl-v-healthy {
  color: var(--vp-c-green-1);
  font-weight: 700;
}
.bl-v-neutral {
  color: var(--vp-c-text-2);
  font-weight: 700;
}
</style>
