import os

import requests

REQUEST_TIMEOUT = 6
DEFAULT_PAGE_SIZE = 100
MAX_PAGES = 20


class ExternalAPIError(Exception):
    """Raised when the furniture shop API can't be reached or isn't configured."""


def _base_url():
    base = os.environ.get("FURNITURE_API_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ExternalAPIError("FURNITURE_API_BASE_URL is not set.")
    return base


def _auth_headers():
    api_key = os.environ.get("FURNITURE_API_KEY", "").strip()
    if not api_key:
        raise ExternalAPIError("FURNITURE_API_KEY is not set.")
    return {"X-Api-Key": api_key}


def _get(path, **kwargs):
    try:
        response = requests.get(f"{_base_url()}{path}", timeout=REQUEST_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ExternalAPIError(str(exc)) from exc


def _post(path, json=None, **kwargs):
    try:
        response = requests.post(f"{_base_url()}{path}", json=json, timeout=REQUEST_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ExternalAPIError(str(exc)) from exc


def get_categories():
    """List every category name from the live catalogue."""
    return _get("/catalogue/categories")


def search_products(category=None, limit=DEFAULT_PAGE_SIZE, skip=0):
    """One page of `/catalogue/search-index` results - no images, fast."""
    params = {"limit": limit, "skip": skip}
    if category:
        params["category"] = category
    return _get("/catalogue/search-index", params=params)


def search_all_products(category=None, page_size=DEFAULT_PAGE_SIZE, max_pages=MAX_PAGES):
    """Page through search-index until exhausted, without assuming the
    server's exact page-size limit - just what it actually hands back.
    """
    results = []
    skip = 0
    for _ in range(max_pages):
        page = search_products(category=category, limit=page_size, skip=skip)
        if not page:
            break
        results.extend(page)
        if len(page) < page_size:
            break
        skip += page_size
    return results


def get_product_detail(item_id):
    """Full detail for one catalogue item, including its photo - unlike
    search-index, image_url here is real (base64-encoded image data, despite
    the field name), so this is slow enough to only use per-item, not for
    listing pages. Returns None if item_id isn't in the live catalogue (some
    locally-seeded products predate it and were never assigned a real one)."""
    try:
        response = requests.get(f"{_base_url()}/catalogue/{item_id}", timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ExternalAPIError(str(exc)) from exc


def get_balance(user_id):
    """The live balance for the given user_id (must match the API key's own user)."""
    return _get(f"/users/{user_id}", headers=_auth_headers())


def submit_order(user_id, items):
    """Report a completed order to the event API. items is a list of
    {"item_id": ..., "quantity": ...} dicts."""
    return _post("/orders", json={"user_id": user_id, "items": items}, headers=_auth_headers())
