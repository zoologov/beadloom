# Catalogue

`entities/product` holds a print: its store loads the catalogue through `shared/api`, and
its card draws one print. `entities/cart` holds what the visitor has picked.

`features/add-to-cart` puts a print into the cart; `features/apply-coupon` takes a code at
checkout. `widgets/product-grid` lays the catalogue out and `widgets/site-header` shows the
cart's count on every page.

Two shortcuts are known and kept visible until they are fixed: the coupon reads the
add-to-cart feature directly, and the product grid reaches into the product store past the
entity's public API.
