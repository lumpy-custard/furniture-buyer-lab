from flask import session

from .models import Product

CART_SESSION_KEY = "cart"


def get_cart():
    return session.get(CART_SESSION_KEY, {})


def save_cart(cart):
    session[CART_SESSION_KEY] = cart


def clear_cart():
    session.pop(CART_SESSION_KEY, None)


def cart_item_count():
    return sum(get_cart().values())


def get_cart_lines():
    """Cart contents joined with current product data, clamped to available stock.

    Returns (lines, removed_count). Any cart entry whose product no longer
    exists is silently pruned from the saved cart and counted in
    removed_count, so the caller can show a friendly message instead of
    letting it vanish without explanation - or crash.
    """
    cart = get_cart()
    if not cart:
        return [], 0

    product_ids = [int(pid) for pid in cart]
    products = {product.id: product for product in Product.query.filter(Product.id.in_(product_ids)).all()}

    lines = []
    removed = 0
    pruned_cart = dict(cart)
    for pid, requested_quantity in cart.items():
        product = products.get(int(pid))
        if not product:
            pruned_cart.pop(pid, None)
            removed += 1
            continue
        quantity = min(requested_quantity, product.available_quantity)
        lines.append(
            {
                "product": product,
                "requested_quantity": requested_quantity,
                "quantity": quantity,
                "subtotal": product.price * quantity,
                "insufficient_stock": quantity < requested_quantity,
            }
        )

    if removed:
        save_cart(pruned_cart)
    return lines, removed
