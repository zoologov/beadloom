# Powered by (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/powered-by/`

---

## Overview

`PoweredBy` is the footer of every page, laid out by the owner's ruling of 2026-10-09 (BDL-080
S4d). The first line is Beadloom's small icon and the text "Powered by Beadloom", which links to
Beadloom's repository. The second line is "MIT" and a link to the same repository drawn with the
GitHub mark the header draws: VitePress's own `VPSocialLink`, at its 20 by 20 pixel size. The
footer is about Beadloom rather than about the adopter, so its links are the same on every
portal, and it is the one place Beadloom's icon appears on an adopter's portal. The adopter's own
logo is in the nav (`site.logo`).

The `app` layer mounts it in the default theme's `layout-bottom` slot. It renders nothing when
the theme's `poweredBy` is `false`, which `.vitepress/config.mjs` sets from
`site.powered_by: false` through the generated identity.

The icon is `public/brand/beadloom-icon.svg`, a monochrome knock-out in a rounded square. It is
drawn as a CSS mask over `currentColor`, so it takes the text's colour in the light and the dark
theme: an SVG drawn as an image cannot inherit the page's `currentColor`. VitePress hides its own
footer beside a sidebar, and this one instead takes the sidebar's width as left padding from
960 pixels up, the way the page content does, so that its lines centre under the content.

## Public API

- `PoweredBy` (Vue component, no props).

## Depends on

- No slice. It imports `vitepress` and `vitepress/theme`.

## Tests

`src/beadloom/site_scaffold/e2e/brand.spec.js` reads each rule against the identity the portal
was generated with, so it holds on a portal either way: the footer has its two lines, the icon
drawn from the brand file, both links to Beadloom's repository, the GitHub mark at 20 by 20, and
nothing covering the first link; with the footer switched off, no footer. The same spec checks
what `.vitepress/config.mjs` sets: the favicon, the nav logo when one is declared and none
otherwise, and the header's repository link with its forge's icon, or no link.
