# Powered by (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/powered-by/`

---

## Overview

`PoweredBy` is the footer of every page, laid out by the owner's ruling of 2026-10-09 (BDL-080
S4d) and corrected by the owner's look at it the same day (S4e). The first line is Beadloom's
small icon and the text "Powered by Beadloom", without a link. The second line is "MIT" and a
link to Beadloom's repository drawn with the GitHub mark the header draws: VitePress's own
`VPSocialLink`, at its 20 by 20 pixel size. The footer is about Beadloom rather than about the
adopter, so its link is the same on every portal, and it is the one place Beadloom's icon appears
on an adopter's portal: the adopter's own logo is in the nav (`site.logo`), and it is the
adopter's favicon too.

The `app` layer mounts it in the default theme's `layout-bottom` slot. It renders nothing when
the theme's `poweredBy` is `false`, which `.vitepress/config.mjs` sets from
`site.powered_by: false` through the generated identity.

The icon is `public/brand/beadloom-icon.svg`, the square icon that is Beadloom's only mark: a
monochrome knock-out in a rounded square. It is
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
drawn from the brand file, the first line's text with no link and nothing covering it, the second
line's link to Beadloom's repository with the GitHub mark at 20 by 20; with the footer switched
off, no footer. The same spec checks what `.vitepress/config.mjs` sets: the favicon (Beadloom's
SVG and its PNG on a portal without a logo of its own, the logo as it is on a portal with one),
the nav logo when one is declared and none otherwise, a logo drawn in `currentColor` painted in
the text's colour at 32 by 32 pixels in either theme, and the header's repository link with its
forge's icon, or no link.
