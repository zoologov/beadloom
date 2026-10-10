# Beadloom's brand sources

These files are the sources of Beadloom's brand, kept in the repository and shipped
nowhere: no package, portal or page reads this folder. Beadloom ships one mark, the
monochrome square icon, drawn in the colour of the text around it, and every shipped
brand file is a source here, byte for byte. `beadloom-icon.svg` ships as
`src/beadloom/site_scaffold/public/brand/beadloom-icon.svg`, the portal's footer icon
and this repository's nav logo; `beadloom-favicon.svg` ships as
`src/beadloom/site_favicon/beadloom-favicon.svg`, the theme-adaptive favicon from which
`tests/support/render_favicon_png.mjs` renders its two PNGs; `social-preview-square.svg`
is `.github/social-preview.svg`, the repository's social preview. The colour files and
the traced mark (`beadloom-mark.svg`, `beadloom-mark-mono.svg` and
`beadloom-icon-gradient.svg`) are sources only, by the owner's ruling of 2026-10-10:
Beadloom ships no colour brand asset. A change to a shipped file is made here first and
copied over, and `tests/unit/application/site/test_the_brand_sources_are_kept_beside_what_ships_from_them.py`
holds the two byte for byte.
