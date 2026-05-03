<script setup>
// DiagramViewer — enhances the Mermaid SVGs rendered by
// `vitepress-plugin-mermaid` with pan + wheel-zoom + reset (svg-pan-zoom) and
// a fullscreen toggle (Fullscreen API).
//
// It renders no visible markup of its own; on mount it finds every `.mermaid`
// container in the document, wraps the SVG in an interactive frame, and adds a
// small control overlay. With JS disabled the page still shows the static
// Mermaid SVG untouched (graceful degradation) — VitePress SSR emits the SVG
// and this enhancement only runs in the browser.

import { onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRoute } from "vitepress";

const route = useRoute();
const ATTACHED = "data-bl-pz"; // marks a container we've already enhanced
const instances = [];

function isBrowser() {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

function destroyAll() {
  while (instances.length) {
    const pz = instances.pop();
    try {
      pz.destroy();
    } catch {
      // svg-pan-zoom may already be detached if the SVG was removed.
    }
  }
}

function makeButton(label, title, onClick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "bl-pz-btn";
  btn.textContent = label;
  btn.title = title;
  btn.setAttribute("aria-label", title);
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    onClick();
  });
  return btn;
}

function toggleFullscreen(frame) {
  if (!document.fullscreenElement) {
    if (frame.requestFullscreen) {
      frame.requestFullscreen().catch(() => {});
    }
  } else if (document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  }
}

async function enhance(container, svgPanZoom) {
  const svg = container.querySelector("svg");
  if (!svg) {
    return;
  }
  container.setAttribute(ATTACHED, "true");
  container.classList.add("bl-pz-frame");

  // svg-pan-zoom needs explicit dimensions on the SVG to compute its viewport.
  svg.style.maxWidth = "none";
  svg.style.width = "100%";
  svg.style.height = "100%";

  const pz = svgPanZoom(svg, {
    zoomEnabled: true,
    panEnabled: true,
    controlIconsEnabled: false,
    fit: true,
    center: true,
    minZoom: 0.2,
    maxZoom: 20,
    zoomScaleSensitivity: 0.3,
    dblClickZoomEnabled: false,
  });
  instances.push(pz);

  const controls = document.createElement("div");
  controls.className = "bl-pz-controls";
  controls.appendChild(
    makeButton("+", "Zoom in", () => pz.zoomIn()),
  );
  controls.appendChild(
    makeButton("−", "Zoom out", () => pz.zoomOut()),
  );
  controls.appendChild(
    makeButton("↺", "Reset view", () => {
      pz.resize();
      pz.fit();
      pz.center();
    }),
  );
  controls.appendChild(
    makeButton("⛶", "Toggle fullscreen", () => {
      toggleFullscreen(container);
      // Re-fit shortly after the fullscreen transition completes.
      window.setTimeout(() => {
        try {
          pz.resize();
          pz.fit();
          pz.center();
        } catch {
          // ignore — container may have been torn down
        }
      }, 150);
    }),
  );
  container.appendChild(controls);
}

async function enhanceAll() {
  if (!isBrowser()) {
    return;
  }
  const containers = Array.from(
    document.querySelectorAll(`.mermaid:not([${ATTACHED}])`),
  );
  if (containers.length === 0) {
    return;
  }
  let svgPanZoom;
  try {
    const mod = await import("svg-pan-zoom");
    svgPanZoom = mod.default ?? mod;
  } catch {
    // Dependency unavailable — leave the static SVGs as-is.
    return;
  }
  for (const container of containers) {
    if (!container.hasAttribute(ATTACHED)) {
      await enhance(container, svgPanZoom);
    }
  }
}

let onFsChange;

// Retry a few times because Mermaid renders its SVGs asynchronously after the
// component mounts (and again after each client-side navigation).
function scheduleEnhance() {
  if (!isBrowser()) {
    return;
  }
  let tries = 0;
  const tick = () => {
    enhanceAll();
    tries += 1;
    if (tries < 8) {
      window.setTimeout(tick, 300);
    }
  };
  nextTick(tick);
}

onMounted(() => {
  if (!isBrowser()) {
    return;
  }
  scheduleEnhance();

  // On client-side navigation the previous SVGs are gone; drop stale
  // svg-pan-zoom instances and enhance the freshly rendered diagrams.
  watch(
    () => route.path,
    () => {
      destroyAll();
      scheduleEnhance();
    },
  );

  onFsChange = () => {
    for (const pz of instances) {
      try {
        pz.resize();
        pz.fit();
        pz.center();
      } catch {
        // ignore detached instances
      }
    }
  };
  document.addEventListener("fullscreenchange", onFsChange);
});

onBeforeUnmount(() => {
  if (!isBrowser()) {
    return;
  }
  if (onFsChange) {
    document.removeEventListener("fullscreenchange", onFsChange);
  }
  destroyAll();
});
</script>

<template>
  <!-- No visible markup: this component enhances the in-page Mermaid SVGs. -->
  <span class="bl-diagram-viewer" aria-hidden="true" />
</template>
