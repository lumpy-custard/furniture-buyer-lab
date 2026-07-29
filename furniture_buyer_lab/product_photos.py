import base64
import io
import os

from flask import url_for
from PIL import Image, ImageFilter, ImageOps

# Keep these in sync with --blueprint-bg / --blueprint-line in style.css - the
# generated sketches sit alongside the hand-drawn procedural ones in
# product_art.py, so they need to look like the same house style.
BLUEPRINT_BG = (18, 41, 79)
BLUEPRINT_LINE = (215, 233, 255)

SKETCH_CANVAS_SIZE = 320
SKETCH_DIR = os.path.join(os.path.dirname(__file__), "static", "product_sketches")


def sketch_filename(sku):
    return f"{sku}.png"


def sketch_path(sku):
    return os.path.join(SKETCH_DIR, sketch_filename(sku))


def has_sketch(sku):
    return os.path.exists(sketch_path(sku))


def sketch_image_url(product):
    """The URL for product's generated photo-sketch, or None if it doesn't
    have one yet (falls back to the procedural product_sketch() line art)."""
    if not has_sketch(product.sku):
        return None
    return url_for("static", filename=f"product_sketches/{sketch_filename(product.sku)}")


def _make_sketch(image_bytes):
    """Turn a real product photo into a blueprint-style line sketch: pad to a
    square on white, edge-detect, then recolour onto the same navy/light-blue
    palette the rest of the site's line art uses."""
    photo = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    side = max(photo.size)
    padded = Image.new("RGB", (side, side), (255, 255, 255))
    padded.paste(photo, ((side - photo.width) // 2, (side - photo.height) // 2))
    padded = padded.resize((SKETCH_CANVAS_SIZE, SKETCH_CANVAS_SIZE), Image.LANCZOS)

    edges = padded.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges, cutoff=1)
    edges = edges.point(lambda p: min(255, int(p * 1.7)))

    canvas = Image.new("RGB", edges.size, BLUEPRINT_BG)
    line_layer = Image.new("RGB", edges.size, BLUEPRINT_LINE)
    canvas.paste(line_layer, mask=edges)
    return canvas


def save_sketch_from_base64(sku, image_b64):
    """Decode a base64 product photo, sketch-ify it, and cache it to disk
    keyed by sku. Raises on bad/undecodable image data - callers should
    treat that the same as "no photo available" for this item."""
    image_bytes = base64.b64decode(image_b64)
    sketch = _make_sketch(image_bytes)
    os.makedirs(SKETCH_DIR, exist_ok=True)
    sketch.save(sketch_path(sku), format="PNG")
