<script setup>
// beadloom:component=site-diagram-viewer
// DiagramViewer — enhances the Mermaid SVGs rendered by
// `vitepress-plugin-mermaid` with pan + wheel-zoom + reset (svg-pan-zoom) and
// a fullscreen toggle (Fullscreen API).
//
// It renders no visible markup of its own; on mount it finds every `.mermaid`
// container in the document, wraps the SVG in an interactive frame, and adds a
// small control overlay. With JS disabled the page still shows the static
// Mermaid SVG untouched (graceful degradation) — VitePress SSR emits the SVG
// and this enhancement only runs in the browser.
//
// `vitepress-plugin-mermaid` renders a diagram again whenever an attribute of
// `<html>` changes (the theme switch among them), replacing the SVG inside the
// same container. The mark of an enhanced diagram is therefore on the SVG, not
// on its container, and a mutation observer enhances each new SVG; in an
// earlier version the mark sat on the container, so a re-rendered diagram lost its
// pan, its controls and its base-aware click targets.

import { onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRoute } from "vitepress";
import { isBrowser } from "../../../shared/lib/index.js";

const route = useRoute();
const ATTACHED = "data-bl-pz"; // marks an SVG we've already enhanced
const instances = [];
let observer = null;

// SVG xlink namespace — Mermaid renders flowchart `click <id> "<url>"`
// directives as `<a xlink:href="<url>">` wrappers around the node group.
const XLINK_NS = "http://www.w3.org/1999/xlink";

// Root-absolute internal path prefixes the generator emits (base-agnostic).
// A click target starting with one of these is an in-site page that must be
// served under the configured base (e.g. `/orders/`).
// Every node page lives under one of the first four; a kind with no directory
// of its own writes its page under `/other/`.
const INTERNAL_PREFIXES = ["/services/", "/domains/", "/features/", "/other/", "/docs/"];

// Make a raw Mermaid click target base-aware. Pure + idempotent: a root-absolute
// internal path gets `base` prepended exactly once; anything else (external URL,
// in-page anchor, relative path, or a value already under `base`) is returned
// unchanged. `base` is VitePress's configured base (e.g. "/orders/", always
// trailing-slashed; "/" when unset).
function baseAwareHref(raw, base) {
  if (!raw || !base || base === "/") {
    return raw;
  }
  const normBase = base.endsWith("/") ? base : `${base}/`;
  if (raw.startsWith(normBase)) {
    return raw; // already base-prefixed
  }
  const isInternal = INTERNAL_PREFIXES.some((p) => raw.startsWith(p));
  if (!isInternal) {
    return raw; // external / anchor / relative — leave untouched
  }
  // raw begins with "/", normBase ends with "/": join without doubling the slash.
  return normBase + raw.slice(1);
}

// Rewrite every clickable anchor inside a rendered diagram so its target
// resolves under the configured base. Mermaid stores the link in `xlink:href`
// (SVG) and may mirror it in `href`; rewrite whichever is present.
function rewriteClickTargets(svg, base) {
  if (base === "/" || !base) {
    return;
  }
  for (const anchor of Array.from(svg.querySelectorAll("a"))) {
    const xlink = anchor.getAttributeNS(XLINK_NS, "href");
    if (xlink) {
      const next = baseAwareHref(xlink, base);
      if (next !== xlink) {
        anchor.setAttributeNS(XLINK_NS, "href", next);
      }
    }
    const plain = anchor.getAttribute("href");
    if (plain) {
      const next = baseAwareHref(plain, base);
      if (next !== plain) {
        anchor.setAttribute("href", next);
      }
    }
  }
}

function destroyAll() {
  while (instances.length) {
    const { pz } = instances.pop();
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
  // A container whose SVG was rendered again drops the pan-zoom of the old one.
  for (let i = instances.length - 1; i >= 0; i -= 1) {
    if (instances[i].container !== container) continue;
    try {
      instances[i].pz.destroy();
    } catch {
      // The old SVG is already detached.
    }
    instances.splice(i, 1);
  }
  svg.setAttribute(ATTACHED, "true");
  container.classList.add("bl-pz-frame");

  // Base-aware click targets: VitePress rewrites markdown/nav links during the
  // build, but Mermaid's raw `click "/services/…"` directives are not — so a
  // diagram node would 404 at the site root under a project-page base. Prepend
  // the configured base here, on the rendered SVG, so the Markdown stays
  // base-agnostic + deterministic. (import.meta.env.BASE_URL is "/" when unset.)
  rewriteClickTargets(svg, import.meta.env.BASE_URL);

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
  instances.push({ container, pz });

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
  const containers = Array.from(document.querySelectorAll(".mermaid")).filter((container) => {
    const svg = container.querySelector("svg");
    return svg && !svg.hasAttribute(ATTACHED);
  });
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
    if (!container.querySelector("svg")?.hasAttribute(ATTACHED)) {
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
    for (const { pz } of instances) {
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

  // A diagram rendered again (a new SVG in its container) is enhanced again.
  observer = new MutationObserver(() => enhanceAll());
  observer.observe(document.body, { childList: true, subtree: true });
});

onBeforeUnmount(() => {
  if (!isBrowser()) {
    return;
  }
  if (onFsChange) {
    document.removeEventListener("fullscreenchange", onFsChange);
  }
  observer?.disconnect();
  observer = null;
  destroyAll();
});
</script>

<template>
  <!-- No visible markup: this component enhances the in-page Mermaid SVGs. -->
  <span class="bl-diagram-viewer" aria-hidden="true" />
</template>
