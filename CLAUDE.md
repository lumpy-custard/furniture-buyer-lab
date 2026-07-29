# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask web app for a hackathon/lab exercise (see `requirements.md`): a buyer-seller scenario where a "buyer" application lets a user browse a supplier's product catalogue and fulfill orders against a budgeted bank account. The exercise builds up in levels:

- **Level 1** (current state): domain model, web UI, login, persistence, workflow/controller logic, reports.
- **Level 2**: external API calls (email, calendar invites, audio transcription, LLM text generation/summarization), receiving webhooks.
- **Level 3**: an agent with Open Claw integration, vector RAG for a product Q&A bot, OCR.
- **Level 4**: more advanced RAG / Q&A bot work.

New feature work should be understood in the context of which level it's building toward.

## Commands

- Run the dev server: `python -m furniture_buyer_lab.app` (serves on `http://127.0.0.1:5000`, debug mode with auto-reload).
- Sync the product catalog from MongoDB: `flask --app furniture_buyer_lab sync-catalog` (see Catalog sync below).
- Install dependencies: `pip install -e .` into the `.venv` (dependencies are declared in `pyproject.toml`; there is no lockfile).
- No test suite exists yet.

## Environment

- Config is loaded from a `.env` file (gitignored) via `python-dotenv`, loaded at import time in `furniture_buyer_lab/__init__.py`. See `.env.example` for required variables (currently `MONGODB_URI`, used only by the catalog sync).

## Architecture

- **App factory**: `furniture_buyer_lab/__init__.py`'s `create_app()` wires up Flask-SQLAlchemy (`db`), Flask-Login (`login_manager`), registers the `auth` and `main` blueprints, and registers CLI commands from `catalog_sync.py`.
- **Blueprints**: `auth_bp` (`/auth/...`) handles login, registration, and forgot/reset password. `main_bp` (`/`) handles the product catalogue view and order placement.
- **Data model**: see `architecture.md` for the full class diagram. Core relationships: `User` 1–1 `BankAccount`, `User` 1–* `Order` / `OrderRequest`, `Order` 1–* `OrderItem` → `Product`, `Supplier` 1–* `Product`.
- **Database / schema changes**: SQLite at `instance/app.db` (gitignored). Schema is created via `db.create_all()` only in `create_app()` — there is **no Flask-Migrate/Alembic**, so `create_all()` creates missing tables but never alters existing ones. Adding or changing a column on an existing table requires either a manual `ALTER TABLE` against `instance/app.db`, or deleting that file so `create_all()` rebuilds it from scratch (which wipes all local data — users, orders, synced catalog). Prefer the manual `ALTER TABLE` route once real data exists.
- **Catalog sync** (`furniture_buyer_lab/catalog_sync.py`): pulls documents from an external MongoDB `catalog` collection (an IKEA product dataset used for the hackathon) and upserts them into the local `Product` table, matched by `sku` (Mongo's `item_id`). It's idempotent/safe to re-run. Products still referenced by existing `OrderItem` rows are intentionally *kept* rather than deleted during sync, since `order_item.product_id` is a NOT NULL FK and SQLAlchemy would otherwise raise an `IntegrityError` trying to null it out.
- **Password reset**: no email provider is configured yet (that's Level 2 work). `auth.py`'s forgot-password flow generates a token and surfaces the reset link directly via flash message + console print rather than emailing it.
