# Catalogue

`entities/product` holds a print: its store loads the catalogue through `shared/api`, and
its card draws one print. `entities/cart` holds what the visitor has picked; it reads a
print's type through `entities/product/@x/cart`, the cross-import API the product opens for
the cart alone.

`features/add-to-cart` puts a print into the cart; `features/apply-coupon` takes a code at
checkout. `features/payment` is a group of two slices, `card-form` and `pay-button`, both on
the checkout page. `widgets/product-grid` lays the catalogue out and `widgets/site-header`
shows the cart's count on every page.

Three shortcuts are known and kept visible until they are fixed: the coupon reads the
add-to-cart feature directly, the pay button reads the card form's details directly although
the two slices of the payment group share no code, and the product grid reaches into the
product store past the entity's public API.
