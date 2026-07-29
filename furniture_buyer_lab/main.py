import time
from math import ceil

from flask import Blueprint, jsonify, render_template, redirect, session, url_for, request, flash
from flask_login import login_required, current_user

from . import assistant
from .cart import get_cart, save_cart, get_cart_lines
from .external_api import ExternalAPIError, get_categories, search_all_products
from .models import Product, Order
from .orders import CheckoutError, place_order
from . import db

# The traditional shop is being phased out in favour of the AI assistant -
# this deliberate delay is a nudge to steer people there, not a performance bug.
SHOP_PAGE_DELAY_SECONDS = 2.5

CATALOGUE_PAGE_SIZE = 24

main_bp = Blueprint("main", __name__)


def _pagination_pages(current, total, radius=2):
    """Page numbers to render, with None standing in for an ellipsis gap."""
    pages = sorted({1, total, current, *range(current - radius, current + radius + 1)} & set(range(1, total + 1)))
    result = []
    previous = None
    for page in pages:
        if previous is not None and page - previous > 1:
            result.append(None)
        result.append(page)
        previous = page
    return result


@main_bp.route("/")
@login_required
def assistant_home():
    session["last_shop_view"] = "assistant"
    return render_template(
        "assistant.html",
        history=assistant.get_display_history(current_user.id),
        assistant_name=assistant.get_assistant_name(current_user.id),
    )


@main_bp.route("/assistant/chat", methods=["POST"])
@login_required
def assistant_chat():
    message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not message:
        return jsonify({"error": "Type a message first."}), 400
    try:
        reply, products = assistant.send_message(current_user.id, message)
    except assistant.AssistantError as exc:
        return jsonify({"error": str(exc)}), 503
    return jsonify({"reply": reply, "products": products})


@main_bp.route("/assistant/reset", methods=["POST"])
@login_required
def assistant_reset():
    assistant.reset_conversation(current_user.id)
    return redirect(url_for("main.assistant_home"))


@main_bp.route("/shop")
@login_required
def home():
    time.sleep(SHOP_PAGE_DELAY_SECONDS)
    session["last_shop_view"] = "shop"

    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    catalogue_error = None
    api_products = []
    categories = []
    try:
        api_products = search_all_products(category=category or None)
        categories = get_categories()
    except ExternalAPIError:
        catalogue_error = "The live product catalogue is temporarily unavailable. Please try again shortly."

    if search:
        needle = search.lower()
        api_products = [p for p in api_products if needle in (p.get("product_name") or "").lower()]

    item_ids = [p.get("item_id") for p in api_products if p.get("item_id")]
    local_by_sku = {}
    if item_ids:
        local_by_sku = {p.sku: p for p in Product.query.filter(Product.sku.in_(item_ids)).all()}

    catalogue_items = [
        {
            "item_id": item.get("item_id"),
            "name": item.get("product_name") or "Unnamed product",
            "category": item.get("category") or "General",
            "price": item.get("price") or 0,
            "local": local_by_sku.get(item.get("item_id")),
        }
        for item in api_products
    ]

    total_count = len(catalogue_items)
    total_pages = max(1, ceil(total_count / CATALOGUE_PAGE_SIZE))
    page = max(1, min(request.args.get("page", 1, type=int) or 1, total_pages))
    start = (page - 1) * CATALOGUE_PAGE_SIZE
    page_items = catalogue_items[start : start + CATALOGUE_PAGE_SIZE]

    return render_template(
        "home.html",
        catalogue_items=page_items,
        catalogue_error=catalogue_error,
        categories=categories,
        search=search,
        selected_category=category,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        pagination_pages=_pagination_pages(page, total_pages),
    )


@main_bp.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get(product_id)
    if product is None:
        flash("This item is no longer available.")
        return redirect(url_for("main.home"))
    return render_template(
        "product_detail.html",
        product=product,
        search=request.args.get("q", ""),
        selected_category=request.args.get("category", ""),
    )


@main_bp.route("/orders")
@login_required
def order_history():
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("orders.html", orders=orders)


@main_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    redirect_args = {
        key: value
        for key, value in {"q": request.form.get("q", ""), "category": request.form.get("category", "")}.items()
        if value
    }

    product = Product.query.get(product_id)
    if product is None:
        flash("This item is no longer available.")
        return redirect(url_for("main.home", **redirect_args))

    quantity = int(request.form.get("quantity", 1))
    if quantity < 1 or quantity > product.available_quantity:
        flash("Invalid quantity selected.")
        return redirect(url_for("main.home", **redirect_args))

    cart = get_cart()
    key = str(product_id)
    new_quantity = min(cart.get(key, 0) + quantity, product.available_quantity)
    cart[key] = new_quantity
    save_cart(cart)

    flash(f"Added {product.name} to cart.")
    return redirect(url_for("main.home", **redirect_args))


@main_bp.route("/cart")
@login_required
def view_cart():
    lines, removed = get_cart_lines()
    if removed:
        flash(
            "This item is no longer available."
            if removed == 1
            else f"{removed} items in your cart are no longer available."
        )
    total = sum(line["subtotal"] for line in lines)
    continue_endpoint = "main.home" if session.get("last_shop_view") == "shop" else "main.assistant_home"
    return render_template("cart.html", lines=lines, total=total, continue_url=url_for(continue_endpoint))


@main_bp.route("/cart/update/<int:product_id>", methods=["POST"])
@login_required
def update_cart_item(product_id):
    quantity = int(request.form.get("quantity", 0))
    cart = get_cart()
    key = str(product_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        product = Product.query.get(product_id)
        if product is None:
            flash("This item is no longer available.")
            cart.pop(key, None)
        else:
            cart[key] = min(quantity, product.available_quantity)
    save_cart(cart)
    return redirect(url_for("main.view_cart"))


@main_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def remove_cart_item(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    return redirect(url_for("main.view_cart"))


@main_bp.route("/orders/<int:order_id>/return", methods=["POST"])
@login_required
def return_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    if order.status != "completed":
        flash("This order can't be returned.")
        return redirect(url_for("main.order_history"))

    for item in order.items:
        if item.product:
            item.product.available_quantity += item.quantity

    order.account.balance += order.total_price
    order.status = "returned"
    db.session.commit()

    flash(f"Order #{order.id} returned — ${order.total_price:.2f} refunded to your account.")
    return redirect(url_for("main.order_history"))


@main_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    try:
        order, warning = place_order(current_user)
    except CheckoutError as exc:
        flash(str(exc))
        return redirect(url_for("main.view_cart"))

    if warning:
        flash(warning)
    flash("Order placed successfully.")
    return redirect(url_for("main.order_history"))
