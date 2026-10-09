<script setup>
// beadloom:component=site-powered-by
// PoweredBy — the footer of every page. Line 1 is Beadloom's small icon and
// "Powered by Beadloom", line 2 is "MIT" and a link to Beadloom's repository
// drawn with the GitHub mark the header draws, the same component at the same
// size. The footer is
// about Beadloom, not about the adopter, so its links are Beadloom's own on
// every portal; it is the one place Beadloom's icon appears on an adopter's
// portal, and `site.powered_by: false` removes it whole (`theme.poweredBy`).
//
// The icon is `public/brand/beadloom-icon.svg`, drawn as a mask over
// `currentColor` so that it takes the text's colour in either theme: an SVG
// drawn as an image cannot inherit the page's `currentColor`.
//
// VitePress hides its own footer beside a sidebar, which is fixed and would
// cover it; this one is kept clear of the sidebar the way the page content is.

import { computed } from "vue";
import { useData, withBase } from "vitepress";
import { VPSocialLink, useSidebar } from "vitepress/theme";

/** Beadloom's repository: both lines of the footer link to it. */
const BEADLOOM_REPOSITORY = "https://github.com/zoologov/beadloom";
const ICON = "/brand/beadloom-icon.svg";

const { theme } = useData();
const { hasSidebar } = useSidebar();

const shown = computed(() => theme.value.poweredBy !== false);
const iconStyle = computed(() => ({ "--bl-powered-by-icon": `url("${withBase(ICON)}")` }));
</script>

<template>
  <footer v-if="shown" class="bl-powered-by" :class="{ 'has-sidebar': hasSidebar }" data-testid="powered-by">
    <p class="bl-powered-by-line" data-powered-by="name">
      <span class="bl-powered-by-icon" :style="iconStyle" aria-hidden="true" data-powered-by="icon"></span>
      <a :href="BEADLOOM_REPOSITORY" target="_blank" rel="noopener">Powered by Beadloom</a>
    </p>
    <p class="bl-powered-by-line" data-powered-by="licence">
      <span>MIT</span>
      <VPSocialLink icon="github" :link="BEADLOOM_REPOSITORY" aria-label="Beadloom on GitHub" />
    </p>
  </footer>
</template>

<style scoped>
.bl-powered-by {
  border-top: 1px solid var(--vp-c-gutter);
  padding: 20px 24px;
  background-color: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  font-size: 14px;
  font-weight: 500;
  line-height: 24px;
}

.bl-powered-by-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 0;
}

.bl-powered-by-line a:not(.VPSocialLink) {
  text-decoration-line: underline;
  text-underline-offset: 2px;
  transition: color 0.25s;
}

.bl-powered-by-line a:not(.VPSocialLink):hover {
  color: var(--vp-c-text-1);
}

.bl-powered-by-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  background-color: currentColor;
  -webkit-mask: var(--bl-powered-by-icon) center / contain no-repeat;
  mask: var(--bl-powered-by-icon) center / contain no-repeat;
}

@media (min-width: 960px) {
  .bl-powered-by.has-sidebar {
    padding-left: calc(var(--vp-sidebar-width) + 32px);
  }
}

@media (min-width: 1440px) {
  .bl-powered-by.has-sidebar {
    padding-right: calc((100vw - var(--vp-layout-max-width)) / 2 + 32px);
    padding-left: calc((100vw - var(--vp-layout-max-width)) / 2 + var(--vp-sidebar-width) + 32px);
  }
}
</style>
