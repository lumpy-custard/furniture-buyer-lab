import json
import os
import random

import openai
from flask import g, render_template
from flask_login import current_user
from openai import AzureOpenAI

from .cart import get_cart, get_cart_lines, save_cart
from .external_api import ExternalAPIError, get_balance, search_all_products
from .models import Product
from .orders import CheckoutError, place_order as _place_order

MAX_COMPLETION_TOKENS = 2048
MAX_HISTORY_MESSAGES = 40  # keep conversations from growing unbounded
MAX_TOOL_ITERATIONS = 8  # guard against a runaway tool-call loop

ASSISTANT_NAMES = [
    "Sage", "Milo", "Nova", "Theo", "Wren", "Juno", "Remy", "Ivy",
    "Oscar", "Nora", "Finn", "Robin",
]

SYSTEM_PROMPT_TEMPLATE = """You are {name}, a furniture shopping specialist for this store. You're friendly and to the point.

Tools: search_catalogue (search by name and/or exact category), show_product
(display a specific item's picture and details to the customer - use this
whenever you recommend or discuss a specific item, don't just describe it in
words), check_balance, add_to_cart, view_cart, and place_order (finalize the
purchase).

When a customer wants help furnishing a room, ask what room, roughly what
budget, and what they care about most - one short question at a time, not a
list. Once you have enough, search, show 1-3 good options with show_product,
add what fits to the cart, and state the running total.

If a customer already knows what they want, skip straight to finding and
showing it.

place_order is real money leaving the customer's account - it charges their
balance, decrements stock, and can't be undone from the chat. Never call it
while just building or adjusting a cart. Only call it once the customer has
clearly confirmed they want to buy the current cart now (e.g. "yes, place the
order", "checkout") - a vague "sounds good" about your suggestions is not
confirmation. Ask if unsure.

search_catalogue only does an exact category match and a substring match on
name - it can't filter by colour, style, or vibe. If asked for something like
that, pull a broader set yourself and judge which fit, rather than claiming
the search can do more than it can.

Keep replies SHORT - one to three sentences, plain language, no headers or
bullet lists unless summarizing a multi-item cart. If a search, balance
check, or order fails, say so plainly rather than making something up."""

# In-memory per-user conversation history and assistant persona. This is a
# lab/dev app running as a single process - fine for now, but it resets on
# restart and won't work across multiple worker processes. A real deployment
# would persist this in the database instead.
_CONVERSATIONS = {}
_ASSISTANT_NAMES = {}


def get_assistant_name(user_id):
    """A random name is assigned the first time a user starts a conversation
    and kept for its lifetime; reset_conversation clears it so the next chat
    gets a fresh one."""
    if user_id not in _ASSISTANT_NAMES:
        _ASSISTANT_NAMES[user_id] = random.choice(ASSISTANT_NAMES)
    return _ASSISTANT_NAMES[user_id]


def reset_conversation(user_id):
    _CONVERSATIONS.pop(user_id, None)
    _ASSISTANT_NAMES.pop(user_id, None)


def get_display_history(user_id):
    """The stored history includes tool-call plumbing - flatten it down to
    just the human-readable turns for rendering in the chat UI."""
    return [
        {"role": msg["role"], "text": msg["content"]}
        for msg in _CONVERSATIONS.get(user_id, [])
        if msg["role"] in ("user", "assistant") and msg.get("content")
    ]


def search_catalogue(query="", category=""):
    """Search the live furniture catalogue by product name and/or exact category."""
    try:
        products = search_all_products(category=category or None)
    except ExternalAPIError as exc:
        return f"The catalogue is temporarily unavailable ({exc}). Tell the customer and suggest trying again shortly."

    if query:
        needle = query.lower()
        products = [p for p in products if needle in (p.get("product_name") or "").lower()]

    if not products:
        return "No products matched that search."

    lines = [
        f"- {p.get('item_id')}: {p.get('product_name')} | {p.get('category')} | ${(p.get('price') or 0):.2f}"
        for p in products[:12]
    ]
    suffix = f"\n(showing 12 of {len(products)} matches - narrow the search for more specific results)" if len(products) > 12 else ""
    return "item_id: name | category | price\n" + "\n".join(lines) + suffix


def check_balance():
    """Check the customer's current live account balance."""
    user_id = os.environ.get("FURNITURE_API_USER_ID", "").strip()
    if not user_id:
        return "Balance is unavailable right now (account isn't configured)."
    try:
        data = get_balance(user_id)
    except ExternalAPIError as exc:
        return f"Balance is unavailable right now ({exc})."
    return f"Current balance: ${data.get('balance', 0):.2f}"


def add_to_cart(item_id, quantity=1):
    """Add a catalogue item to the customer's shopping cart."""
    product = Product.query.filter_by(sku=item_id).first()
    if product is None:
        return f"Couldn't find item {item_id} - it may no longer be available. Try searching again."
    if quantity < 1:
        return "Quantity must be at least 1."
    if quantity > product.available_quantity:
        return f"Only {product.available_quantity} of '{product.name}' are in stock."

    cart = get_cart()
    key = str(product.id)
    cart[key] = min(cart.get(key, 0) + quantity, product.available_quantity)
    save_cart(cart)

    lines, _ = get_cart_lines()
    total = sum(line["subtotal"] for line in lines)
    return (
        f"Added {quantity} x '{product.name}' (${product.price:.2f} each) to the cart. "
        f"Cart now has {len(lines)} line item(s) totaling ${total:.2f}."
    )


def show_product(item_id):
    """Display a specific item's picture and details to the customer in the chat."""
    product = Product.query.filter_by(sku=item_id).first()
    if product is None:
        return f"Couldn't find item {item_id} - it may no longer be available. Try searching again."

    cards = g.setdefault("assistant_product_cards", [])
    cards.append(render_template("_product_chat_card.html", product=product))
    return f"Shown to the customer: {product.name}, ${product.price:.2f}."


def view_cart():
    """View the customer's current shopping cart contents and total."""
    lines, _ = get_cart_lines()
    if not lines:
        return "The cart is currently empty."
    rows = [f"- {line['quantity']} x {line['product'].name} = ${line['subtotal']:.2f}" for line in lines]
    total = sum(line["subtotal"] for line in lines)
    return "\n".join(rows) + f"\nTotal: ${total:.2f}"


def place_order():
    """Finalize the purchase for everything currently in the customer's cart.

    Only call this after the customer has explicitly confirmed they want to
    buy the current cart - it really charges their balance and empties the
    cart, it isn't reversible from the chat.
    """
    try:
        order, warning = _place_order(current_user)
    except CheckoutError as exc:
        return str(exc)
    message = f"Order #{order.id} placed successfully - ${order.total_price:.2f} charged to your account."
    if warning:
        message += f" Note: {warning}"
    return message


TOOL_FUNCTIONS = {
    "search_catalogue": search_catalogue,
    "show_product": show_product,
    "check_balance": check_balance,
    "add_to_cart": add_to_cart,
    "view_cart": view_cart,
    "place_order": place_order,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_catalogue",
            "description": "Search the live furniture catalogue by product name and/or exact category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text search matched against the product name (optional).",
                    },
                    "category": {
                        "type": "string",
                        "description": 'An exact category name to filter by, e.g. "Chairs" (optional).',
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_product",
            "description": "Display a specific item's picture and details to the customer in the chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The item_id string returned by search_catalogue.",
                    },
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_balance",
            "description": "Check the customer's current live account balance.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a catalogue item to the customer's shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The item_id string returned by search_catalogue.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "How many to add (default 1).",
                    },
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "View the customer's current shopping cart contents and total.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": (
                "Finalize the purchase for everything currently in the customer's cart - charges their "
                "balance, decrements stock, and empties the cart. Only call after explicit customer confirmation."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class AssistantError(Exception):
    """Raised when the assistant can't be reached - missing/invalid config, network failure, etc."""


def _client_config():
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "").strip()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
    if not (endpoint and api_key and api_version and deployment):
        raise AssistantError("The shopping assistant isn't configured yet (missing Azure OpenAI settings).")
    return endpoint, api_key, api_version, deployment


def send_message(user_id, user_message):
    """Run one turn of the shopping-assistant chat for user_id, keeping
    conversation history server-side across requests. Returns (reply_text,
    product_cards) where product_cards is a list of rendered HTML snippets
    for any items show_product displayed during this turn."""
    endpoint, api_key, api_version, deployment = _client_config()
    g.assistant_product_cards = []

    name = get_assistant_name(user_id)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(name=name)

    messages = _CONVERSATIONS.get(user_id, []) + [{"role": "user", "content": user_message}]
    llm_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)

        reply_text = None
        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.chat.completions.create(
                model=deployment,
                messages=llm_messages,
                tools=TOOLS_SCHEMA,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )
            message = response.choices[0].message
            assistant_entry = {"role": "assistant", "content": message.content}
            if message.tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                    }
                    for tool_call in message.tool_calls
                ]
            llm_messages.append(assistant_entry)

            if not message.tool_calls:
                reply_text = message.content
                break

            for tool_call in message.tool_calls:
                func = TOOL_FUNCTIONS.get(tool_call.function.name)
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = func(**args) if func else f"Unknown tool: {tool_call.function.name}"
                llm_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    except openai.OpenAIError as exc:
        raise AssistantError(f"The shopping assistant is temporarily unavailable ({exc}).") from exc

    messages.append({"role": "assistant", "content": reply_text or ""})
    _CONVERSATIONS[user_id] = messages[-MAX_HISTORY_MESSAGES:]
    product_cards = g.assistant_product_cards

    if reply_text is None:
        return "Sorry, that took too many steps - please try rephrasing your request.", product_cards
    return reply_text or "...", product_cards
