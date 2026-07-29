# Brand & Style Guide

This is the reference for any visual or UI work on Furniture Buyer Lab. It documents the design language already implemented in `furniture_buyer_lab/static/css/style.css` and `furniture_buyer_lab/product_art.py` — treat this as the source of truth for extending it, not a wishlist.

## Brand essence

- **Personality**: a small, well-run neighborhood furniture shop — warm and approachable, not corporate. Confident and clean, never flashy.
- **Mark, not wordmark**: the brand is represented by a small icon (a simple sofa/storefront glyph, currently inline SVG in `base.html`'s `.brand` link) with no accompanying text. There is intentionally no visible "Furniture Buyer Lab" title anywhere in the UI — identity comes from consistent color, type, and illustration style, not a logotype. If a wordmark is ever needed (e.g. for an external doc), use plain text in the body typeface — do not design a custom logotype.
- **Tone in copy**: short, plain, human. "Add to cart", "Only 3 left", "Order placed successfully" — no exclamation marks, no marketing language.

## Color system

Defined as CSS custom properties in `style.css` `:root`, with a full dark-mode override set. Always reference the variable, never hard-code a hex value in a template or new stylesheet — that's what makes both themes work automatically.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f5f6fa` | `#14161c` | Page background |
| `--surface` | `#ffffff` | `#1c1f27` | Cards, inputs, the topbar |
| `--border` | `#e6e8ef` | `#2a2e38` | Hairline borders, dividers |
| `--text` | `#1a1d29` | `#e7e9ee` | Primary text |
| `--text-muted` | `#6b7280` | `#9aa1ae` | Secondary text, meta info |
| `--primary` | `#4f46e5` | `#6366f1` | Buttons, links, focus rings, brand mark |
| `--primary-hover` | `#4338ca` | `#7c7ff2` | Hover state for primary actions |
| `--primary-tint` | `#eef2ff` | `rgba(99,102,241,.18)` | Category badges, flash banners |
| `--success-tint` / `--success-text` | `#dcfce7` / `#166534` | `rgba(34,197,94,.16)` / `#4ade80` | "Completed" status |
| `--warning-tint` / `--warning-text` | `#fef3c7` / `#92400e` | `rgba(245,158,11,.16)` / `#fbbf24` | Low-stock badges |
| `--danger-tint` / `--danger-text` | `#fee2e2` / `#b91c1c` | `rgba(248,113,113,.18)` / `#f87171` | Out-of-stock badges |
| `--info-tint` / `--info-text` | `#dbeafe` / `#1e40af` | `rgba(59,130,246,.18)` / `#93c5fd` | "Created" order status |
| `--neutral-tint` / `--neutral-text` | `#e5e7eb` / `#374151` | `rgba(148,163,184,.18)` / `#cbd5e1` | "Returned" order status |

Dark values are tinted/translucent (`rgba`) rather than flat pastel hex for the tint pairs — a flat light pastel would look like a washed-out patch on a dark card, so dark-mode tints are low-alpha overlays of the same hue instead.

### Blueprint tokens (fixed, not themed)

| Token | Value | Use |
|---|---|---|
| `--blueprint-bg` | `#12294f` | Product sketch panel background (deep navy) |
| `--blueprint-line` | `#d7e9ff` | Sketch line color |
| `--blueprint-grid` | `rgba(215,233,255,.10)` | Faint graph-paper grid behind the sketch |

These three are declared once in `:root` and are **not** overridden by dark mode — a blueprint drawing looks the same regardless of what light is in the room. Every product visual (`.product-visual`, `.cart-thumb`, `.pdp-visual`) is a fixed navy panel with a subtle grid-paper texture (two `repeating-linear-gradient` layers) in both themes; only the surrounding UI chrome (cards, text, nav) follows light/dark.

Radii: `--radius` (14px, cards) and `--radius-sm` (10px, buttons/inputs/badges' inner corners — badges themselves are fully pill-shaped). Elevation: `--shadow` at rest, `--shadow-hover` on hover — soft and low-contrast in light mode, slightly higher-alpha in dark mode so cards still read as elevated against a dark background.

### Dark / light mode

Themeable via three layers, in `style.css`:

1. `:root { ... }` — light values, the default.
2. `@media (prefers-color-scheme: dark) { :root { ... } }` — automatically switches to dark values when the OS/browser reports a dark preference and the user hasn't explicitly overridden it.
3. `:root[data-theme="light"]` / `:root[data-theme="dark"]` — explicit override. The attribute-selector rules have higher specificity than the plain `:root` inside the media query, so an explicit choice always wins over the system default in both directions.

The toggle button in the topbar (`#theme-toggle`, wired in `static/js/theme.js`) flips between light and dark, persists the explicit choice to `localStorage["theme"]`, and swaps its own icon (sun/moon) to match. If the user has never toggled it, the page follows the OS setting live — including reacting to the OS theme changing while the tab is open. A small inline script in `base.html`'s `<head>` applies any saved explicit preference before first paint, so there's no flash of the wrong theme on load.

**Rule for new UI**: never write `background: white` or similar literal light-mode-only values — always a token, so it inherits both themes for free.

## Typography

- **Typeface**: Inter (Google Fonts), loaded in `base.html`. Fallback stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- **Base size**: 15px body text, 1.5 line-height.
- **Weights in use**: 400 (body), 600 (labels, badges, buttons), 700 (headings, prices, totals). Don't introduce 500 or anything above 700.
- **Section titles** (`.section-title`): 20px / 700. Card headings use the same weight at a smaller size where nested.
- Letter-spacing is very slightly tightened (`-0.01em`) on headings only — never on body text or buttons.

## Iconography & illustration style: blueprint drawings

This is the most distinctive part of the brand and the part most likely to need extending (new product categories, new icon needs elsewhere in the app). The system lives in `furniture_buyer_lab/product_art.py`. Blueprint/technical-line-art is a real, current design direction for product-forward sites (not just a house style choice here) — stark line drawings on a fixed panel color, in the spirit of an architectural or patent drawing, not a decorative sketch.

**Principle**: every illustration is a *technical line drawing of the actual thing*, traced onto a fixed navy "blueprint" panel with a faint grid-paper texture behind it (see Blueprint tokens above) — not a photo, not a flat colored icon, not a warm pencil sketch. Precise over cozy.

**Color rule**: illustrations never carry their own hue and never follow the site's light/dark toggle. Every sketch renders in `stroke="currentColor"`; `.product-visual svg` / `.cart-thumb svg` / `.pdp-visual svg` all set that color to `var(--blueprint-line)` against `var(--blueprint-bg)`. If you want the catalogue to feel more varied, vary the *drawing* (proportion, geometry) — never reach for a color palette on the illustrations.

**Uniqueness is data-driven, not decorative.** The catalogue sync bakes real `Dimensions (WxDxH): {w}x{d}x{h} cm` text into each product's description. `_parse_dimensions` in `product_art.py` reads it back out and uses the real width/height — compared against a per-category `REFERENCE_DIMENSIONS` baseline — to set each drawing's x/y scale. A 220cm sofa actually draws wider than a 160cm one; a genuinely tall wardrobe draws taller than a squat one. Only when a product has no parseable dimensions (a couple of legacy placeholder items) does it fall back to a SKU-hashed pseudo-random scale. This is the main lever for "not generic" — reach for real data before reaching for more random jitter.

### How it's built (so it stays cheap, unique per item, and consistent)

1. **Draw the object as clean geometry first.** Each category (`CATEGORY_STROKES`) is a small list of *strokes* on a fixed 0–120 canvas: mostly straight-line polylines (open or closed), plus the occasional true `circle`/`ellipse` for small crisp details (handles, wheels, a tabletop rim). Keep shapes simple and recognizable in silhouette — a chair is a seat/back rectangle plus two splayed legs, nothing more.
2. **Scale it from real dimensions.** `_style_for` parses the product's actual cm dimensions and derives independent x/y scale factors against a category reference size (see Uniqueness above). This runs before anything else — it's what makes two products in the same category structurally different drawings, not two copies of one template.
3. **Wobble it, lightly.** Every polyline is subdivided and its *interior* points are jittered by a small offset (`_wobble`, jitter ~0.8–1.3px). True corner points are never moved, so strokes that share a corner (a tabletop meeting a leg) still meet exactly. This is deliberately subtle — a blueprint is hand-traced, not sketchy — much tighter than a loose pencil-sketch wobble would be.
4. **Double-stroke it.** Each line is drawn twice with two independent jitter seeds: a soft, thin underlay (`opacity 0.35`) and a crisper top line — like a drawing traced twice, once light and once firm.
5. **Annotate it — detail view only.** `product_sketch(product, detailed=True)` (used on the product detail page, not the compact grid thumbnail) adds three technical-drawing conventions: corner crop-marks framing the panel, dimension callout lines with the product's *real* width/height in cm, and a title-block-style `NO. {sku}` label. The compact grid thumbnail omits these so they don't clutter a small image — see Product grid & detail page below.
6. **Vary it per product, not per render.** Every random choice — jitter, a small ±3° tilt, an occasional horizontal flip — is seeded from a hash of the product's SKU (`_rng_for`). The same product always renders identically.
7. **No runtime filters.** Deliberately *not* using SVG `feTurbulence`/`feDisplacementMap` or any other GPU/CPU-heavy filter — everything is precomputed static path data. With 700+ items rendered on a single catalogue page, this keeps render cost roughly equivalent to plain SVG (verified: page paints in well under a second for the full catalogue). Any future illustration work should preserve this constraint.

### Adding a new category or illustration

- Stay inside the 0–120 viewBox convention (grid thumbnail) so new icons drop into the existing containers without resizing; the detail view expands the viewBox with margin for annotations (`-22 -20 164 188`) — don't change that margin without checking the corner-tick/dimension-line positions still fit.
- Use 3–6 strokes maximum. More detail doesn't read as more precise at icon size — it reads as clutter once wobbled.
- Prefer straight-line strokes; reserve `circle`/`ellipse` for small round details that should stay crisp (wobble is intentionally *not* applied to these).
- Add a `REFERENCE_DIMENSIONS` entry (typical width/height in cm) for any new category — without one it silently falls back to `DEFAULT_REFERENCE`, which works but won't scale as meaningfully against real catalogue data.
- Never assign a category its own color. If a category needs to feel distinct, do it through silhouette, not hue — color is reserved for UI chrome (badges, buttons, status), never the drawing itself.
- Always route new illustrations through `_render_geometry` / `_style_for` rather than writing one-off inline SVG.

## Layout & components

- **Cards** (`.card`, `.product-card`, order cards): white surface, `--radius`, `--shadow`, hover lifts to `--shadow-hover` with a small `translateY(-3px to -4px)`.
- **Buttons**: `.btn-primary` (solid indigo, filled actions), `.btn-ghost` (bordered, secondary/nav actions). No third button style — if something needs more emphasis than ghost but less than primary, that's a sign the page has too many competing actions, not a cue to add a new button variant.
- **Badges**: pill-shaped, tinted background + matching text color, always from the semantic palette (category = primary tint, stock state = success/warning/danger tint).
- **Status tags** (order history): same pill pattern, one color per status (`completed` = success, `pending` = warning, `created` = info/blue, `returned` = neutral gray). A new order status should get its own single tint pair here rather than reusing an existing one with a different meaning.
- **Forms**: label above input, `--radius-sm`, focus ring is a 3px `--primary-tint` glow plus a `--primary` border — no browser default focus outline.

### Product grid & detail page

Following the industry-standard "product-as-hero, detail-on-click" pattern (minimal grid card, full detail on its own page) rather than cramming everything into every card:

- **Grid card** (`.product-card-compact`, `home.html`): blueprint thumbnail (1:1, no annotations) → name (truncated to one line) → price → a stock badge *only* when low/out → a single quick "Add to cart" button (always quantity 1 — no quantity stepper in the grid). No category badge, no description in the grid; the grid's job is fast scanning and one-click add, not full information. `.product-grid-compact` uses a tighter `minmax(148px, 1fr)` track so more items show per row than a generic `.product-grid`.
- **Product detail page** (`/product/<id>`, `product_detail.html`, `.pdp`): the image and name/description/price/quantity-selector live here instead. Large annotated blueprint (`detailed=True`) on the left, full info + quantity + add-to-cart on the right. This is where category badge, full description, and exact stock count belong.
- Clicking a grid card's image *or* name navigates to the detail page; the "Add to cart" button stays a quick-add that never navigates. Don't blur that distinction by making the whole card a link — the button must stay independently clickable.

### Navigation & account menu

- Primary nav (`base.html` topbar): brand mark, then — for signed-in users — "Shop" and "Cart" as direct links (frequent, single-purpose actions belong in the open nav, not behind a menu), then a **profile menu**.
- **Profile menu** (`.profile-menu` / `#profile-trigger` / `#profile-panel`, wired in `static/js/nav.js`): a discreet trigger (small circular initial avatar + name) that opens a dropdown with a name/email header, then account-scoped actions that don't need to be one click away: "Order history", the dark/light mode toggle (as a menu item, not a separate icon, when signed in), and "Logout" (styled with `--danger-text`, since it ends the session). This mirrors the standard e-commerce "discreet person icon → dropdown" convention rather than listing every account action as its own nav button.
- The dropdown closes on: clicking a link item, clicking outside, or Escape. Don't add a menu item that requires a second click elsewhere to take effect (e.g. a settings toggle needing a separate "Save") — every item should act immediately, like the theme toggle does.
- On unauthenticated pages (login/register/forgot-password) there's no profile menu to hold it, so the theme toggle appears as a standalone icon button in the same nav slot instead. Same `#theme-toggle` id and `static/js/theme.js` logic either way — only the surrounding markup (`.profile-menu-item` vs standalone `.theme-toggle` button) differs, and `theme.js` branches on that class to decide whether to render an icon-only button or an icon+label menu row.

## Motion

Motion is restrained and functional only: card hover lift/shadow (~0.15–0.18s ease), sketch icon micro-scale-and-tilt on card hover (~0.25s ease), button active-state press (`translateY(1px)`). Nothing auto-plays, nothing loops, nothing longer than ~0.25s.

## Do

- Reuse existing CSS custom properties before adding new colors or spacing values.
- Keep new illustrations inside the hand-drawn sketch system described above.
- Keep copy short and literal.

## Don't

- Don't reintroduce a visible text wordmark/title in the UI.
- Don't add a new button color/variant, a new shadow depth, or a new radius value without a clear, reused purpose — the whole system is deliberately small.
- Don't use photos, flat/filled icons, or per-item colored line art for products — everything is a monochrome blueprint line drawing on the fixed navy panel; reach for real-dimension proportion variation instead of color.
- Don't let the blueprint panel follow light/dark mode — it's intentionally fixed (`--blueprint-*`, not overridden in the dark block), like real blueprint paper.
- Don't hard-code a light-mode-only color anywhere else; always use a token so dark mode gets it for free.
- Don't add runtime SVG filters or other per-frame-expensive effects to the catalogue grid; it renders 700+ items on one page.
- Don't put full product detail (description, quantity stepper, category badge) back into the grid card — that belongs on the product detail page. The grid is for scanning and quick-add only.
- Don't add more standalone icon buttons to the signed-in topbar for account-scoped actions — fold them into the profile menu instead, so the primary nav stays to "Shop" and "Cart".
