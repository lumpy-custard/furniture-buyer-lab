import hashlib
import random
import re

from markupsafe import Markup

# Each shape is a list of strokes on a 0-120 canvas. A stroke is either:
#   ("line", [(x, y), ...])          - an open or closed polyline
#   ("circle", cx, cy, r)
#   ("ellipse", cx, cy, rx, ry)
# Polylines get a light hand-traced wobble at render time; circles/ellipses
# stay crisp so small details (handles, wheels) read cleanly. Everything
# renders as a blueprint-style line drawing - see the module docstring below
# for how the right shape and per-product uniqueness are chosen.
SHAPE_STROKES = {
    "chair": [
        ("line", [(34, 20), (86, 20), (86, 66), (34, 66), (34, 20)]),
        ("line", [(34, 66), (26, 106)]),
        ("line", [(86, 66), (94, 106)]),
        ("line", [(34, 20), (28, 12)]),
        ("line", [(86, 20), (92, 12)]),
    ],
    "armchair": [
        ("line", [(30, 66), (90, 66), (90, 90), (30, 90), (30, 66)]),
        ("line", [(38, 48), (82, 48), (82, 66), (38, 66)]),
        ("line", [(30, 52), (40, 52), (40, 90)]),
        ("line", [(90, 52), (80, 52), (80, 90)]),
        ("line", [(36, 90), (36, 98)]),
        ("line", [(84, 90), (84, 98)]),
    ],
    "sofa": [
        ("line", [(16, 70), (104, 70), (104, 92), (16, 92), (16, 70)]),
        ("line", [(28, 50), (92, 50), (92, 70), (28, 70)]),
        ("line", [(16, 54), (28, 54), (28, 92)]),
        ("line", [(104, 54), (92, 54), (92, 92)]),
        ("line", [(24, 92), (24, 100)]),
        ("line", [(96, 92), (96, 100)]),
    ],
    "ottoman": [
        ("line", [(36, 50), (84, 50), (84, 86), (36, 86), (36, 50)]),
        ("line", [(36, 68), (84, 68)]),
        ("line", [(42, 86), (42, 98)]),
        ("line", [(78, 86), (78, 98)]),
    ],
    "stool": [
        ("line", [(40, 50), (80, 50), (80, 60), (40, 60), (40, 50)]),
        ("line", [(44, 60), (38, 102)]),
        ("line", [(76, 60), (82, 102)]),
        ("line", [(52, 60), (50, 100)]),
        ("line", [(68, 60), (70, 100)]),
    ],
    "bench": [
        ("line", [(18, 54), (102, 54), (102, 64), (18, 64), (18, 54)]),
        ("line", [(24, 64), (22, 100)]),
        ("line", [(96, 64), (98, 100)]),
    ],
    "bar_stool": [
        ("ellipse", 60, 34, 14, 5),
        ("line", [(60, 39), (60, 80)]),
        ("line", [(60, 80), (44, 104)]),
        ("line", [(60, 80), (76, 104)]),
        ("line", [(50, 64), (70, 64)]),
    ],
    "bar_stool_backrest": [
        ("ellipse", 60, 34, 14, 5),
        ("line", [(60, 34), (60, 10)]),
        ("line", [(50, 10), (70, 10)]),
        ("line", [(60, 39), (60, 80)]),
        ("line", [(60, 80), (44, 104)]),
        ("line", [(60, 80), (76, 104)]),
        ("line", [(50, 64), (70, 64)]),
    ],
    "bar_table": [
        ("ellipse", 60, 26, 26, 7),
        ("line", [(60, 33), (60, 79)]),
        ("line", [(60, 79), (40, 100)]),
        ("line", [(60, 79), (80, 100)]),
        ("line", [(46, 60), (74, 60)]),
    ],
    "table": [
        ("line", [(14, 34), (106, 34), (106, 44), (14, 44), (14, 34)]),
        ("line", [(22, 44), (18, 90)]),
        ("line", [(98, 44), (102, 90)]),
        ("line", [(50, 44), (48, 90)]),
        ("line", [(70, 44), (72, 90)]),
    ],
    "bed": [
        ("line", [(14, 56), (106, 56), (106, 90), (14, 90), (14, 56)]),
        ("line", [(14, 56), (14, 32), (34, 32), (34, 56)]),
        ("line", [(22, 68), (42, 68), (42, 80), (22, 80), (22, 68)]),
        ("line", [(14, 90), (14, 98)]),
        ("line", [(106, 90), (106, 98)]),
    ],
    "kids": [
        ("line", [(40, 26), (80, 26), (80, 60), (40, 60), (40, 26)]),
        ("line", [(40, 60), (34, 90)]),
        ("line", [(80, 60), (86, 90)]),
        ("circle", 60, 43, 9),
    ],
    "crib": [
        ("line", [(20, 40), (100, 40), (100, 90), (20, 90), (20, 40)]),
        ("line", [(32, 40), (32, 26), (88, 26), (88, 40)]),
        ("line", [(40, 40), (40, 90)]),
        ("line", [(52, 40), (52, 90)]),
        ("line", [(68, 40), (68, 90)]),
        ("line", [(80, 40), (80, 90)]),
        ("line", [(16, 96), (24, 90), (32, 96)]),
        ("line", [(88, 96), (96, 90), (104, 96)]),
    ],
    "lounge": [
        ("line", [(22, 44), (98, 44), (98, 64), (22, 64), (22, 44)]),
        ("line", [(30, 44), (34, 20), (66, 20), (70, 44)]),
        ("line", [(28, 64), (22, 96)]),
        ("line", [(92, 64), (98, 96)]),
    ],
    "divider": [
        ("line", [(20, 14), (20, 106)]),
        ("line", [(60, 10), (60, 110)]),
        ("line", [(100, 14), (100, 106)]),
        ("line", [(20, 30), (60, 22), (100, 30)]),
        ("line", [(20, 90), (60, 98), (100, 90)]),
    ],
    "sideboard": [
        ("line", [(16, 46), (104, 46), (104, 86), (16, 86), (16, 46)]),
        ("line", [(40, 46), (40, 86)]),
        ("line", [(80, 46), (80, 86)]),
        ("circle", 30, 66, 2.5),
        ("circle", 90, 66, 2.5),
        ("line", [(20, 86), (20, 96)]),
        ("line", [(100, 86), (100, 96)]),
    ],
    "tv_unit": [
        ("line", [(18, 66), (102, 66), (102, 96), (18, 96), (18, 66)]),
        ("line", [(34, 30), (86, 30), (86, 58), (34, 58), (34, 30)]),
        ("line", [(50, 66), (50, 58)]),
        ("line", [(70, 66), (70, 58)]),
    ],
    "trolley": [
        ("line", [(26, 22), (94, 22), (94, 74), (26, 74), (26, 22)]),
        ("line", [(26, 46), (94, 46)]),
        ("line", [(38, 74), (38, 84)]),
        ("line", [(82, 74), (82, 84)]),
        ("circle", 38, 92, 8),
        ("circle", 82, 92, 8),
    ],
    "headphones": [
        ("line", [(40, 26), (60, 6), (80, 26)]),
        ("line", [(40, 26), (40, 46)]),
        ("line", [(80, 26), (80, 46)]),
        ("circle", 34, 60, 16),
        ("circle", 86, 60, 16),
    ],
    "box": [
        ("line", [(36, 50), (84, 50), (84, 90), (36, 90), (36, 50)]),
        ("line", [(36, 62), (84, 62)]),
    ],
    "hardware": [
        ("line", [(42, 36), (42, 78), (80, 78)]),
        ("circle", 42, 36, 4),
        ("circle", 80, 78, 4),
        ("circle", 42, 78, 3),
    ],
}

FALLBACK_STROKES = [
    ("line", [(20, 44), (60, 20), (100, 44)]),
    ("line", [(20, 44), (20, 96), (100, 96), (100, 44)]),
    ("line", [(60, 44), (60, 68)]),
]

# The catalogue's `category` field is broad - "Bar furniture" covers bar
# tables AND bar stools, "Café furniture" covers tables, chairs and stools,
# etc - and a large slice of every category is actually small hardware/parts
# (handles, legs, cushion covers, drill templates) rather than a full piece
# of furniture at all. Picking the drawing from category alone made every
# product in a category look identical, including parts that don't look
# anything like the main item. So the shape is chosen in two passes:
#   1. Is this actually just a part/accessory? (exact/prefix/suffix match,
#      not a loose substring - so "Bed frame with storage" is never
#      mistaken for the bare accessory "Frame".)
#   2. Otherwise, match the most specific furniture-type phrase in the name
#      (order matters - "bar stool with backrest" before "bar stool" before
#      "bar table"), falling back to a per-category default only when
#      nothing in the name matches.
BARE_ACCESSORY_NAMES = {
    "frame",
    "handle",
    "leg",
    "legs",
    "hinge",
    "bracket",
    "castor",
    "castors",
    "wheel",
    "wheels",
    "rail",
    "hook",
    "top panel",
    "glass top",
    "lid",
    "mirror",
    "cover",
    "mattress",
    "chair pad",
    "chair cushion",
    "drill template",
    "cross-brace",
    "bottle rack",
    "chopping board",
    "cutting board",
    "corner section cover",
    "leg cover",
    "back cushion",
    "seat cushion",
    "seat/back cushion",
    "door",
    "doors",
    "knob",
    "knobs",
    "screw",
    "screws",
    "connector",
    "bracket set",
    "fixing set",
    "assembly kit",
    "foot",
    "post",
    "plinth",
    "mesh basket",
    "wire basket",
    "clip-on basket",
    "connection fittings",
    "corner fittings",
    "storage case",
    "supporting leg",
    "suspension rail",
    "extra shelf",
    "pair of legs",
    "pair of armrests",
    "smart lock",
    "drawer front",
    "door/drawer front",
    "drawer runner",
    "drawer frame",
    "top and plinth",
    "floor protector",
    "seat shell",
    "net",
    "bed canopy",
    "headrest",
}
ACCESSORY_NAME_PREFIXES = (
    "cover for",
    "inner cushion",
    "rack for",
    "legs for",
    "leg for",
    "hook for",
    "padded seat cover for",
    "seat shell for",
)
# Word endings that are never themselves a whole piece of furniture - safe
# as a suffix check, unlike e.g. "frame", "section" or "castors" which are
# legitimate endings for real items ("Bed frame", "3 sections", "Conference
# chair with castors").
ACCESSORY_NAME_SUFFIXES = (" cover", " cushion", " handle", " knob", " mattress")

NAME_SHAPE_RULES = [
    ("bar stool with backrest", "bar_stool_backrest"),
    ("bar stool", "bar_stool"),
    ("bar table", "bar_table"),
    ("footstool", "ottoman"),
    ("pouffe", "ottoman"),
    ("recliner", "armchair"),
    ("armchair", "armchair"),
    ("armrest", "armchair"),
    ("children", "kids"),
    ("kids", "kids"),
    ("cot", "crib"),
    ("crib", "crib"),
    ("tv bench", "tv_unit"),
    (" tv ", "tv_unit"),
    ("bench", "bench"),
    ("kitchen island", "trolley"),
    ("trolley", "trolley"),
    ("cart", "trolley"),
    ("wardrobe", "wardrobe"),
    ("chest of", "drawers"),
    ("drawer", "drawers"),
    ("bookcase", "bookcase"),
    ("shelving", "bookcase"),
    ("shelf", "bookcase"),
    ("shlf", "bookcase"),
    ("cupboard", "cabinet"),
    ("cabinet", "cabinet"),
    ("storage combination", "cabinet"),
    ("sideboard", "sideboard"),
    ("console", "sideboard"),
    ("buffet", "sideboard"),
    ("sofa", "sofa"),
    ("stool", "stool"),
    ("bed frame", "bed"),
    ("bed", "bed"),
    ("table", "table"),
    ("tbl", "table"),
    ("desk", "table"),
    ("chair", "chair"),
]

CATEGORY_DEFAULT_SHAPE = {
    "Chairs": "chair",
    "Sofas & armchairs": "sofa",
    "Tables & desks": "table",
    "Beds": "bed",
    "Bookcases & shelving units": "bookcase",
    "Cabinets & cupboards": "cabinet",
    "Café furniture": "table",
    "Chests of drawers & drawer units": "drawers",
    "Children's furniture": "kids",
    "Nursery furniture": "crib",
    "Outdoor furniture": "lounge",
    "Room dividers": "divider",
    "Sideboards, buffets & console tables": "sideboard",
    "TV & media furniture": "tv_unit",
    "Trolleys": "trolley",
    "Wardrobes": "wardrobe",
    "Bar furniture": "bar_table",
    "Electronics": "headphones",
}

# Shapes that are actually generated procedurally (drawer/door/shelf count
# drawn from the real product name or dimensions) rather than a fixed
# SHAPE_STROKES template - see _strokes_for.
PARAMETRIC_SHAPES = {"drawers", "wardrobe", "cabinet", "bookcase"}

# Roughly typical width/height in cm for each category - real catalogue
# dimensions are compared against these to size each drawing, so a 220cm
# sofa actually draws wider than a 160cm one instead of every item in a
# category sharing one silhouette.
REFERENCE_DIMENSIONS = {
    "Chairs": (55, 90),
    "Sofas & armchairs": (200, 85),
    "Tables & desks": (120, 75),
    "Beds": (160, 100),
    "Bookcases & shelving units": (80, 190),
    "Cabinets & cupboards": (90, 90),
    "Café furniture": (60, 100),
    "Chests of drawers & drawer units": (80, 90),
    "Children's furniture": (50, 60),
    "Nursery furniture": (70, 90),
    "Outdoor furniture": (70, 90),
    "Room dividers": (100, 180),
    "Sideboards, buffets & console tables": (140, 80),
    "TV & media furniture": (150, 50),
    "Trolleys": (60, 80),
    "Wardrobes": (100, 200),
    "Bar furniture": (50, 100),
    "Electronics": (20, 20),
}
DEFAULT_REFERENCE = (80, 90)

DIMENSION_RE = re.compile(r"Dimensions \(WxDxH\):\s*([\d.?]+)x([\d.?]+)x([\d.?]+)\s*cm", re.IGNORECASE)
COUNT_RE_TEMPLATE = r"(\d+)\s*{}"

CANVAS_CENTER = (60, 60)


def _normalize(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _accessory_shape(name):
    n = _normalize(name)
    if n in BARE_ACCESSORY_NAMES:
        return "hardware"
    if n.startswith("storage box"):
        return "box"
    if any(n.startswith(prefix) for prefix in ACCESSORY_NAME_PREFIXES):
        return "hardware"
    if any(n.endswith(suffix) for suffix in ACCESSORY_NAME_SUFFIXES):
        return "hardware"
    return None


def _shape_key_for(product):
    accessory = _accessory_shape(product.name)
    if accessory:
        return accessory
    name = f" {(product.name or '').lower()} "
    for keyword, shape_key in NAME_SHAPE_RULES:
        if keyword in name:
            return shape_key
    return CATEGORY_DEFAULT_SHAPE.get(product.category, None) or "table"


def _count_from_name(name, keyword):
    match = re.search(COUNT_RE_TEMPLATE.format(keyword), name)
    return int(match.group(1)) if match else None


def _parse_dimensions(description):
    """Pull the real width/depth/height (cm) the catalogue sync baked into
    the description text, e.g. "Dimensions (WxDxH): 80x60x105 cm.". Returns
    None if the product has no such text (legacy placeholder items) or the
    values are unknown ("?").
    """
    match = DIMENSION_RE.search(description or "")
    if not match:
        return None

    def _num(token):
        try:
            return float(token)
        except ValueError:
            return None

    width, depth, height = (_num(token) for token in match.groups())
    if width is None or height is None:
        return None
    return width, depth, height


def _rect(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]


def _drawer_strokes(count):
    count = max(2, min(count, 8))
    strokes = [("line", _rect(24, 16, 96, 108))]
    step = (108 - 16) / count
    for i in range(1, count):
        y = 16 + step * i
        strokes.append(("line", [(24, y), (96, y)]))
    for i in range(count):
        y_mid = 16 + step * (i + 0.5)
        strokes.append(("line", [(52, y_mid), (68, y_mid)]))
    return strokes


def _wardrobe_strokes(door_count, drawer_count=0):
    door_count = max(1, min(door_count, 4))
    drawer_count = max(0, min(drawer_count, 4))
    body_bottom = 112
    split_y = 112 - (drawer_count * 10 if drawer_count else 0)
    split_y = max(70, split_y)
    strokes = [
        ("line", _rect(22, 14, 98, body_bottom)),
        ("line", [(18, 14), (102, 14)]),
    ]
    width = 98 - 22
    step = width / door_count
    for i in range(1, door_count):
        x = 22 + step * i
        strokes.append(("line", [(x, 14), (x, split_y)]))
    for i in range(door_count):
        cx = 22 + step * (i + 1) - step * 0.15
        strokes.append(("circle", cx, 64, 2.5))
    if drawer_count:
        strokes.append(("line", [(22, split_y), (98, split_y)]))
        dstep = (body_bottom - split_y) / drawer_count
        for i in range(1, drawer_count):
            y = split_y + dstep * i
            strokes.append(("line", [(22, y), (98, y)]))
        for i in range(drawer_count):
            y_mid = split_y + dstep * (i + 0.5)
            strokes.append(("line", [(52, y_mid), (68, y_mid)]))
    return strokes


def _cabinet_strokes(door_count):
    door_count = max(1, min(door_count, 3))
    strokes = [("line", _rect(20, 16, 100, 104))]
    width = 100 - 20
    step = width / door_count
    for i in range(1, door_count):
        x = 20 + step * i
        strokes.append(("line", [(x, 16), (x, 104)]))
    for i in range(door_count):
        cx = 20 + step * (i + 1) - step * 0.15
        strokes.append(("circle", cx, 60, 2.5))
    return strokes


def _bookcase_strokes(shelf_count):
    shelf_count = max(2, min(shelf_count, 6))
    strokes = [("line", _rect(22, 12, 98, 108))]
    height = 108 - 12
    step = height / shelf_count
    for i in range(1, shelf_count):
        y = 12 + step * i
        strokes.append(("line", [(22, y), (98, y)]))
    return strokes


def _strokes_for(product, shape_key):
    """Resolve a shape key to actual strokes. Drawer/door/shelf counts come
    from the real product name (or dimensions, for shelves) when available,
    so a "Chest of 6 drawers" actually draws 6 drawers - falling back to a
    SKU-hashed count only when the name doesn't say.
    """
    if shape_key not in PARAMETRIC_SHAPES:
        return SHAPE_STROKES.get(shape_key, FALLBACK_STROKES)

    name = (product.name or "").lower()
    rng = _rng_for(product.sku, "count")

    if shape_key == "drawers":
        count = _count_from_name(name, "drawer") or rng.randint(2, 5)
        return _drawer_strokes(count)
    if shape_key == "wardrobe":
        doors = _count_from_name(name, "door") or rng.randint(1, 3)
        drawers = _count_from_name(name, "drawer") or 0
        return _wardrobe_strokes(doors, drawers)
    if shape_key == "cabinet":
        doors = _count_from_name(name, "door") or rng.randint(1, 2)
        return _cabinet_strokes(doors)
    if shape_key == "bookcase":
        dims = _parse_dimensions(product.description)
        height = dims[2] if dims else None
        shelves = max(2, min(6, round(height / 40))) if height else rng.randint(3, 5)
        return _bookcase_strokes(shelves)
    return FALLBACK_STROKES


def _rng_for(*parts):
    key = ":".join(str(part) for part in parts).encode("utf-8")
    seed = int(hashlib.md5(key).hexdigest(), 16) % (2**31)
    return random.Random(seed)


def _wobble(points, rng, jitter, segments=4):
    """Subdivide a polyline and jitter the interior points for a hand-drawn
    feel. True endpoints are left untouched so strokes that share a corner
    (a tabletop meeting a leg) still meet exactly, keeping the sketch
    legible even though the lines are shaky.
    """
    wobbled = [points[0]]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        for i in range(1, segments + 1):
            t = i / segments
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            if i != segments:
                x += rng.uniform(-jitter, jitter)
                y += rng.uniform(-jitter, jitter)
            wobbled.append((x, y))
    return wobbled


def _path_d(points):
    parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for x, y in points[1:]:
        parts.append(f"L {x:.1f} {y:.1f}")
    return " ".join(parts)


def _scaled(points, sx, sy):
    cx, cy = CANVAS_CENTER
    return [(cx + (x - cx) * sx, cy + (y - cy) * sy) for x, y in points]


def _bounding_box(strokes, sx, sy):
    xs, ys = [], []
    for stroke in strokes:
        kind = stroke[0]
        if kind == "line":
            for x, y in _scaled(stroke[1], sx, sy):
                xs.append(x)
                ys.append(y)
        elif kind == "circle":
            _, cx, cy, r = stroke
            (cx, cy), = _scaled([(cx, cy)], sx, sy)
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        elif kind == "ellipse":
            _, cx, cy, rx, ry = stroke
            (cx, cy), = _scaled([(cx, cy)], sx, sy)
            xs += [cx - rx * sx, cx + rx * sx]
            ys += [cy - ry * sy, cy + ry * sy]
    return min(xs), min(ys), max(xs), max(ys)


def _render_geometry(strokes, sku, sx, sy):
    parts = []
    for index, stroke in enumerate(strokes):
        kind = stroke[0]
        if kind == "line":
            points = _scaled(stroke[1], sx, sy)
            # Two independently-jittered passes of the same stroke: a soft,
            # thin underlay plus a crisper top line, like a technical
            # drawing traced twice rather than plotted by machine.
            under_rng = _rng_for(sku, index, "under")
            top_rng = _rng_for(sku, index, "top")
            under = _wobble(points, under_rng, jitter=1.7)
            top = _wobble(points, top_rng, jitter=1.1)
            parts.append(f'<path d="{_path_d(under)}" stroke-width="2.8" opacity="0.38"/>')
            parts.append(f'<path d="{_path_d(top)}" stroke-width="1.6"/>')
        elif kind == "circle":
            _, cx, cy, r = stroke
            (cx, cy), = _scaled([(cx, cy)], sx, sy)
            jitter_rng = _rng_for(sku, index, "circle")
            dx = jitter_rng.uniform(-0.5, 0.5)
            dy = jitter_rng.uniform(-0.5, 0.5)
            parts.append(f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r * (sx + sy) / 2:.1f}" stroke-width="1.4"/>')
        elif kind == "ellipse":
            _, cx, cy, rx, ry = stroke
            (cx, cy), = _scaled([(cx, cy)], sx, sy)
            parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx * sx:.1f}" ry="{ry * sy:.1f}" stroke-width="1.5"/>')
    return "".join(parts)


def _corner_ticks(x1, y1, x2, y2, length=7):
    """Small L-shaped brackets framing a region, like a technical drawing's
    crop marks."""
    corners = [
        ((x1, y1), (length, 0), (0, length)),
        ((x2, y1), (-length, 0), (0, length)),
        ((x1, y2), (length, 0), (0, -length)),
        ((x2, y2), (-length, 0), (0, -length)),
    ]
    parts = []
    for (x, y), (dx1, dy1), (dx2, dy2) in corners:
        parts.append(
            f'<path d="M {x + dx1:.1f} {y + dy1:.1f} L {x:.1f} {y:.1f} L {x + dx2:.1f} {y + dy2:.1f}" '
            f'stroke-width="1" opacity="0.8"/>'
        )
    return "".join(parts)


def _dimension_line_h(x1, x2, y, label):
    tick = 4
    text = (
        f'<text x="{(x1 + x2) / 2:.1f}" y="{y + 13:.1f}" font-size="7" '
        f'font-family="Menlo, Consolas, monospace" text-anchor="middle" stroke="none" fill="currentColor" opacity="0.85">{label}</text>'
    )
    return (
        f'<path d="M {x1:.1f} {y - tick:.1f} L {x1:.1f} {y + tick:.1f} M {x1:.1f} {y:.1f} L {x2:.1f} {y:.1f} '
        f'M {x2:.1f} {y - tick:.1f} L {x2:.1f} {y + tick:.1f}" stroke-width="0.8" opacity="0.7"/>' + text
    )


def _dimension_line_v(y1, y2, x, label):
    tick = 4
    text = (
        f'<text x="{x - 6:.1f}" y="{(y1 + y2) / 2:.1f}" font-size="7" '
        f'font-family="Menlo, Consolas, monospace" text-anchor="middle" stroke="none" fill="currentColor" opacity="0.85" '
        f'transform="rotate(-90 {x - 6:.1f} {(y1 + y2) / 2:.1f})">{label}</text>'
    )
    return (
        f'<path d="M {x - tick:.1f} {y1:.1f} L {x + tick:.1f} {y1:.1f} M {x:.1f} {y1:.1f} L {x:.1f} {y2:.1f} '
        f'M {x - tick:.1f} {y2:.1f} L {x + tick:.1f} {y2:.1f}" stroke-width="0.8" opacity="0.7"/>' + text
    )


def _style_for(product):
    digest = hashlib.md5(product.sku.encode("utf-8")).hexdigest()
    flip = int(digest[8:10], 16) % 2 == 1
    rotate = (int(digest[10:12], 16) % 7) - 3  # -3..3 degrees, a precise but not-quite-plotted tilt

    ref_w, ref_h = REFERENCE_DIMENSIONS.get(product.category, DEFAULT_REFERENCE)
    dims = _parse_dimensions(product.description)
    if dims:
        width, _depth, height = dims
        sx = max(0.7, min(1.4, width / ref_w))
        sy = max(0.7, min(1.4, height / ref_h))
    else:
        sx = 0.86 + (int(digest[12:14], 16) % 30) / 100.0
        sy = 0.86 + (int(digest[14:16], 16) % 30) / 100.0
    return flip, rotate, sx, sy, dims


def product_sketch(product, detailed=False):
    """Inline blueprint-style technical line drawing.

    The shape is picked from the product's own name (falling back to a
    per-category default only when nothing in the name matches), so
    accessories/hardware get a small generic icon instead of a full-size
    furniture silhouette, and a "Bar stool" draws differently from a "Bar
    table" even though they share a category. Drawer/door/shelf counts for
    storage furniture come from the product's real name text when it's
    there (a "Chest of 6 drawers" actually draws 6 drawers). On top of that,
    the whole drawing is scaled from the product's own catalogue
    width/height, so uniqueness comes from real data, not just decoration.
    `detailed=True` (the product detail page) adds corner crop-marks, a
    title-block SKU label, and dimension callouts with the product's real
    measurements; the compact grid thumbnail omits those so they stay
    legible at small size.
    """
    flip, rotate, sx, sy, dims = _style_for(product)
    shape_key = _shape_key_for(product)
    strokes = _strokes_for(product, shape_key)
    geometry = _render_geometry(strokes, product.sku, sx, sy)
    flip_transform = "scale(-1,1) translate(-120,0) " if flip else ""

    extras = ""
    view_box = "0 0 120 120"
    if detailed:
        view_box = "-22 -20 164 188"
        min_x, min_y, max_x, max_y = _bounding_box(strokes, sx, sy)
        extras += _corner_ticks(-14, -12, 134, 150)
        if dims:
            width, _depth, height = dims
            extras += _dimension_line_h(min_x, max_x, max_y + 16, f"{width:g} cm")
            extras += _dimension_line_v(min_y, max_y, min_x - 14, f"{height:g} cm")
        extras += (
            f'<text x="-14" y="163" font-size="7" font-family="Menlo, Consolas, monospace" '
            f'stroke="none" fill="currentColor" opacity="0.6">NO. {product.sku}</text>'
        )

    svg = (
        f'<svg viewBox="{view_box}" fill="none" stroke="currentColor" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="{flip_transform}rotate({rotate} 60 60)">{geometry}</g>'
        f"{extras}"
        f"</svg>"
    )
    return Markup(svg)
