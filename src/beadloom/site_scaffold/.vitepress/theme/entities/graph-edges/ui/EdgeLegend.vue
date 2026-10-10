<script setup>
// beadloom:component=site-graph-edges
// The legend of the edges that are drawn: one line sample per style key, drawn as the canvas draws it.
//
// A sample is a thin line in the style's dash, ending in its arrowhead, in the
// colour the canvas gives a line of that style at rest. The viewer passes those
// colours, resolved from the theme as the canvas's are (`colours`); until it
// has, a sample takes its tone at its share from the theme's variables. While
// the canvas draws a line of several kinds (`several`), an entry says how such a
// line is drawn, with a solid sample in a neutral tone (`SEVERAL_KINDS`).

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { EDGE_STYLES, SEVERAL_KINDS, dashOf } from "../model/edgeKinds.js";

/** A sample's line and arrowhead, in pixels: the canvas's weight and head. */
const SAMPLE = Object.freeze({ width: 30, height: 10, line: 1.35, head: 6 });

const props = defineProps({
  keys: { type: Array, required: true },
  /** The colour of each style key at rest, as the canvas draws it: `{ [styleKey]: "rgb(...)" }`. */
  colours: { type: Object, default: () => ({}) },
  /** Whether a line of several kinds is drawn now: the legend then names it. */
  several: { type: Boolean, default: false },
});

/** A style's colour from the theme's variables: its tone at its share over the background. */
function themeColour(look) {
  return `color-mix(in srgb, var(${TOKEN_VARIABLES[look.tone]}) ${look.strength * 100}%, var(--vp-c-bg))`;
}

/** The outline of an arrowhead with its tip at the sample's end: a triangle, or a vee. */
function headPoints(shape) {
  const tip = SAMPLE.width - 1;
  const base = tip - SAMPLE.head;
  const middle = SAMPLE.height / 2;
  const half = SAMPLE.head / 2;
  const corners = [
    [tip, middle],
    [base, middle - half],
    ...(shape === "vee" ? [[tip - SAMPLE.head / 2, middle]] : []),
    [base, middle + half],
  ];
  return corners.map((corner) => corner.join(",")).join(" ");
}

/** A legend entry for `look`: its text, its sample's colour (`colour`, or the theme's), dash and head. */
const entryOf = (look, colour) => ({ text: look.legend, colour: colour || themeColour(look), dash: dashOf(look).join(" ") || "none", head: headPoints(look.arrow) });

const entries = computed(() =>
  props.keys.filter((key) => EDGE_STYLES[key]).map((key) => ({ key, ...entryOf(EDGE_STYLES[key], props.colours[key]) }))
);
const severalEntry = computed(() => (props.several ? entryOf(SEVERAL_KINDS) : null));
</script>

<template>
  <span class="bl-legend-group">Edges:</span>
  <span
    v-for="entry in entries"
    :key="entry.key"
    class="bl-legend-item"
    :data-legend-edge="entry.key"
  >
    <svg
      class="bl-legend-line"
      :width="SAMPLE.width"
      :height="SAMPLE.height"
      :viewBox="`0 0 ${SAMPLE.width} ${SAMPLE.height}`"
      aria-hidden="true"
    >
      <line
        data-legend-line
        x1="1"
        :y1="SAMPLE.height / 2"
        :x2="SAMPLE.width - 1 - SAMPLE.head / 2"
        :y2="SAMPLE.height / 2"
        :style="{ stroke: entry.colour, strokeWidth: SAMPLE.line, strokeDasharray: entry.dash }"
      />
      <polygon data-legend-head :points="entry.head" :style="{ fill: entry.colour }" />
    </svg>
    {{ entry.text }}
  </span>
  <span v-if="severalEntry" class="bl-legend-item" data-legend-several>
    <svg
      class="bl-legend-line"
      :width="SAMPLE.width"
      :height="SAMPLE.height"
      :viewBox="`0 0 ${SAMPLE.width} ${SAMPLE.height}`"
      aria-hidden="true"
    >
      <line
        data-legend-line
        x1="1"
        :y1="SAMPLE.height / 2"
        :x2="SAMPLE.width - 1 - SAMPLE.head / 2"
        :y2="SAMPLE.height / 2"
        :style="{ stroke: severalEntry.colour, strokeWidth: SAMPLE.line, strokeDasharray: severalEntry.dash }"
      />
      <polygon data-legend-head :points="severalEntry.head" :style="{ fill: severalEntry.colour }" />
    </svg>
    {{ severalEntry.text }}
  </span>
</template>

<style scoped>
.bl-legend-group {
  font-weight: 700;
  color: var(--vp-c-text-1);
}
.bl-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bl-legend-line {
  display: inline-block;
  flex: none;
}
</style>
