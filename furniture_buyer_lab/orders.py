import os

from . import db
from .cart import get_cart_lines, save_cart
from .external_api import ExternalAPIError, submit_order
from .models import Order, OrderItem


class CheckoutError(Exception):
    """Raised when the current cart can't be checked out as-is - empty, insufficient stock, or insufficient balance."""


def place_order(user):
    """Check out user's current session cart: validate stock/balance, create
    the Order/OrderItem rows, decrement stock and balance, clear the cart, and
    report the completed order to the external furniture shop event API.

    Shared by the web checkout route and the shopping assistant's place_order
    tool so both go through identical validation and bookkeeping.

    Returns (order, warning) on success, where warning describes any cart
    items pruned because they're no longer available and/or a failure to
    sync the order to the external API (or None if nothing to flag).
    Raises CheckoutError with a customer-facing message if checkout can't proceed.
    """
    lines, removed = get_cart_lines()
    warnings = []
    if removed:
        warnings.append(
            "1 item in your cart was no longer available and has been removed."
            if removed == 1
            else f"{removed} items in your cart were no longer available and have been removed."
        )

    if not lines:
        raise CheckoutError(warnings[0] if warnings else "Your cart is empty.")

    for line in lines:
        if line["insufficient_stock"]:
            raise CheckoutError(f"{line['product'].name} no longer has enough stock. Please review your cart.")

    account = user.bank_account
    total_price = sum(line["subtotal"] for line in lines)
    if total_price > account.balance:
        raise CheckoutError("Insufficient balance: you don't have enough budget to complete this purchase.")

    order = Order(user_id=user.id, account_id=account.id, total_price=total_price, status="completed")
    db.session.add(order)
    db.session.commit()

    for line in lines:
        product = line["product"]
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=line["quantity"],
                unit_price=product.price,
                subtotal=line["subtotal"],
            )
        )
        product.available_quantity -= line["quantity"]

    account.balance -= total_price
    db.session.commit()

    save_cart({})

    external_user_id = os.environ.get("FURNITURE_API_USER_ID", "").strip()
    if not external_user_id:
        warnings.append("This order wasn't reported to the training API (no account is configured).")
    else:
        items = [{"item_id": line["product"].sku, "quantity": line["quantity"]} for line in lines]
        try:
            submit_order(external_user_id, items)
        except ExternalAPIError as exc:
            warnings.append(f"This order wasn't reported to the training API ({exc}).")

    return order, " ".join(warnings) if warnings else None
