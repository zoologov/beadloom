<script setup>
// beadloom:component=site-shared
// A terminal command shown as code, with a button that copies it.
//
// The command is copied through the Clipboard API. Where the browser refuses
// it, the command's text is selected instead, so a reader can copy it by hand,
// and the button says so rather than claiming a copy that did not happen.

import { ref } from "vue";

const props = defineProps({
  command: { type: String, required: true },
});

/** How long the button reports the result before it reads "Copy" again, in ms. */
const FEEDBACK_MS = 1600;

const code = ref(null);
const feedback = ref("");
let timer = null;

function report(text) {
  feedback.value = text;
  clearTimeout(timer);
  timer = setTimeout(() => (feedback.value = ""), FEEDBACK_MS);
}

function selectCommand() {
  const range = document.createRange();
  range.selectNodeContents(code.value);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.command);
    report("Copied");
  } catch {
    selectCommand();
    report("Selected");
  }
}
</script>

<template>
  <span class="bl-copy">
    <code ref="code">{{ command }}</code>
    <button type="button" :aria-label="`Copy: ${command}`" :title="`Copy: ${command}`" @click="copy">
      {{ feedback || "Copy" }}
    </button>
  </span>
</template>

<style scoped>
.bl-copy {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 3px 0;
}
.bl-copy code {
  flex: 1 1 auto;
  min-width: 0;
  overflow-x: auto;
  white-space: nowrap;
  font-size: 12px;
}
.bl-copy button {
  flex: 0 0 auto;
  padding: 1px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 5px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 12px;
  cursor: pointer;
}
.bl-copy button:hover {
  border-color: var(--vp-c-brand-1);
}
</style>
