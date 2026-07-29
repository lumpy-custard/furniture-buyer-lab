import os
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import click
from pymongo import MongoClient

from . import db
from .external_api import ExternalAPIError, get_product_detail
from .models import OrderItem, Product, Supplier
from .product_photos import has_sketch, save_sketch_from_base64

SUPPLIER_NAME = "Hackathon IKEA Catalog (MongoDB)"
DEFAULT_AVAILABLE_QUANTITY = 25


def _sanitized_endpoint(uri):
    """Cluster host + path only, with credentials stripped for storage/display."""
    parts = urlsplit(uri)
    return urlunsplit((parts.scheme, parts.hostname or "", parts.path, "", ""))


def _build_description(doc):
    colours = doc.get("colours") or []
    colour_text = "/".join(colours) if colours else "unspecified colour"
    dims = [doc.get("width"), doc.get("depth"), doc.get("height")]
    dims_text = "x".join(f"{d:g}" if isinstance(d, (int, float)) else "?" for d in dims)
    return f"{doc.get('category', 'Furniture')} in {colour_text}. Dimensions (WxDxH): {dims_text} cm."[:400]


def fetch_catalog_documents():
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI environment variable is not set.")
    client = MongoClient(uri)
    database = client.get_default_database()
    return list(database["catalog"].find())


def sync_catalog_from_mongo():
    """Replace the Product catalog with the contents of the MongoDB `catalog` collection."""
    documents = fetch_catalog_documents()

    supplier = Supplier.query.filter_by(name=SUPPLIER_NAME).first()
    if supplier is None:
        supplier = Supplier(name=SUPPLIER_NAME)
        db.session.add(supplier)
    supplier.api_endpoint = _sanitized_endpoint(os.environ["MONGODB_URI"])
    supplier.last_sync_at = datetime.utcnow()
    db.session.flush()

    existing_by_sku = {product.sku: product for product in Product.query.all()}
    incoming_skus = set()

    for doc in documents:
        sku = str(doc.get("item_id") or doc["_id"])
        incoming_skus.add(sku)
        fields = {
            "name": doc.get("product_name", "Unnamed product")[:200],
            "description": _build_description(doc),
            "price": float(doc.get("price") or 0),
            "sku": sku,
            "supplier_id": supplier.id,
            "category": (doc.get("category") or "General")[:100],
        }
        product = existing_by_sku.get(sku)
        if product is None:
            db.session.add(Product(available_quantity=DEFAULT_AVAILABLE_QUANTITY, **fields))
        else:
            for key, value in fields.items():
                setattr(product, key, value)

    stale_products = [product for sku, product in existing_by_sku.items() if sku not in incoming_skus]
    referenced_product_ids = {
        row.product_id
        for row in db.session.query(OrderItem.product_id).filter(
            OrderItem.product_id.in_([p.id for p in stale_products])
        )
    }
    removable = [product for product in stale_products if product.id not in referenced_product_ids]
    kept = len(stale_products) - len(removable)
    for product in removable:
        db.session.delete(product)

    db.session.commit()
    return {"synced": len(documents), "removed": len(removable), "kept_due_to_orders": kept}


def sync_product_photos(limit=None):
    """Fetch each product's real photo from the furniture shop event API and
    cache a generated blueprint-style sketch of it to static/product_sketches/,
    keyed by sku. Per-item and network-bound (the event API only serves
    images one item at a time), so this is a separate, slower command from
    sync-catalog - safe to re-run since products that already have a cached
    sketch are skipped.
    """
    products = Product.query.order_by(Product.id).all()
    if limit:
        products = products[:limit]

    created = skipped = no_photo = failed = 0
    for product in products:
        if has_sketch(product.sku):
            skipped += 1
            continue
        try:
            detail = get_product_detail(product.sku)
        except ExternalAPIError:
            failed += 1
            continue

        if detail is None:
            no_photo += 1
            continue

        image_b64 = detail.get("image_url")
        if not image_b64:
            no_photo += 1
            continue

        try:
            save_sketch_from_base64(product.sku, image_b64)
            created += 1
        except Exception:
            failed += 1

    return {"created": created, "skipped": skipped, "no_photo": no_photo, "failed": failed}


def register_cli(app):
    @app.cli.command("sync-catalog")
    def sync_catalog_command():
        """Replace placeholder products with the MongoDB catalog collection."""
        result = sync_catalog_from_mongo()
        print(
            f"Synced {result['synced']} products, removed {result['removed']} stale products "
            f"({result['kept_due_to_orders']} kept because they have existing orders)."
        )

    @app.cli.command("sync-product-images")
    @click.option("--limit", default=None, type=int, help="Only process the first N products (for testing).")
    def sync_product_images_command(limit):
        """Generate blueprint-style sketches from each product's real photo (via the event API)."""
        result = sync_product_photos(limit=limit)
        print(
            f"Generated {result['created']} new sketches, skipped {result['skipped']} already cached, "
            f"{result['no_photo']} items have no photo, {result['failed']} failed."
        )
