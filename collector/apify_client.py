"""Apify API wrapper for Airbnb data collection."""

import math
from urllib.parse import urlencode

from apify_client import ApifyClient

from config import APIFY_TOKEN, SEARCH_ACTOR_ID, CALENDAR_ACTOR_ID


def _get_client() -> ApifyClient:
    if not APIFY_TOKEN:
        raise ValueError(
            "APIFY_TOKEN not set. Export it as an environment variable or set it in config.py"
        )
    return ApifyClient(APIFY_TOKEN)


def _bounding_box(lat: float, lng: float, radius_km: float) -> dict:
    """Calculate a bounding box around a point given a radius in km.

    Returns dict with ne_lat, ne_lng, sw_lat, sw_lng.
    """
    # 1 degree latitude ≈ 111 km
    delta_lat = radius_km / 111.0
    # 1 degree longitude varies with latitude
    delta_lng = radius_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "ne_lat": round(lat + delta_lat, 6),
        "ne_lng": round(lng + delta_lng, 6),
        "sw_lat": round(lat - delta_lat, 6),
        "sw_lng": round(lng - delta_lng, 6),
    }


def _build_search_url(
    lat: float,
    lng: float,
    radius_km: float = 20,
    min_bedrooms: int = 0,
    min_guests: int = 0,
    check_in: str = "",
    check_out: str = "",
) -> str:
    """Build an Airbnb search URL with bounding box and filters."""
    bb = _bounding_box(lat, lng, radius_km)
    params = {
        "ne_lat": bb["ne_lat"],
        "ne_lng": bb["ne_lng"],
        "sw_lat": bb["sw_lat"],
        "sw_lng": bb["sw_lng"],
        "search_type": "filter",
        "tab_id": "home_tab",
    }
    if min_bedrooms > 0:
        params["min_bedrooms"] = min_bedrooms
    if min_guests > 0:
        params["adults"] = min_guests
    if check_in:
        params["checkin"] = check_in
    if check_out:
        params["checkout"] = check_out
    return f"https://www.airbnb.com/s/homes?{urlencode(params)}"


def search_listings(
    latitude: float,
    longitude: float,
    radius_km: float = 20,
    location: str = "",
    check_in: str = "",
    check_out: str = "",
    min_bedrooms: int = 0,
    max_guests: int = 0,
    max_results: int = 50,
) -> list[dict]:
    """Search Airbnb listings within a radius of given coordinates.

    Uses a bounding box via startUrls for precise geographic filtering.
    Returns a list of normalized listing dicts.
    """
    client = _get_client()

    search_url = _build_search_url(
        lat=latitude,
        lng=longitude,
        radius_km=radius_km,
        min_bedrooms=min_bedrooms,
        min_guests=max_guests,
        check_in=check_in,
        check_out=check_out,
    )

    run_input = {
        "startUrls": [{"url": search_url}],
        "maxResults": max_results,
    }

    run = client.actor(SEARCH_ACTOR_ID).call(run_input=run_input)

    results = []
    for i, item in enumerate(client.dataset(run["defaultDatasetId"]).iterate_items()):
        if i == 0:
            import json, sys
            print("=== RAW APIFY ITEM KEYS ===", file=sys.stderr)
            print(json.dumps({k: repr(v)[:200] for k, v in item.items()}, indent=2), file=sys.stderr)
            print("=== END RAW ===", file=sys.stderr)
        results.append(_normalize_search_result(item))
    return results


def _normalize_search_result(item: dict) -> dict:
    """Normalize Apify search result to a consistent format."""
    # Extract price — may be a dict like {"label": "$120", "amount": 120}
    raw_price = item.get("price", item.get("pricePerNight"))
    if isinstance(raw_price, dict):
        price = raw_price.get("amount", raw_price.get("value"))
        if price is None and "label" in raw_price:
            import re
            nums = re.findall(r"[\d,.]+", str(raw_price["label"]))
            price = float(nums[0].replace(",", "")) if nums else None
    elif raw_price is not None:
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            import re
            nums = re.findall(r"[\d,.]+", str(raw_price))
            price = float(nums[0].replace(",", "")) if nums else None
    else:
        price = None

    # Extract rating — may be a dict like {"accuracy": 4.8, ...} or a number
    raw_rating = item.get("rating", item.get("stars"))
    if isinstance(raw_rating, dict):
        rating = raw_rating.get("overall", raw_rating.get("value"))
        if rating is None:
            # Average all sub-ratings
            nums = [v for v in raw_rating.values() if isinstance(v, (int, float))]
            rating = round(sum(nums) / len(nums), 2) if nums else None
    elif raw_rating is not None:
        try:
            rating = float(raw_rating)
        except (TypeError, ValueError):
            rating = None
    else:
        rating = None

    # Extract thumbnail — may be in images list, thumbnail field, or picture
    thumbnail = item.get("thumbnail", item.get("picture", ""))
    if not thumbnail:
        images = item.get("images", item.get("photos", []))
        if images and isinstance(images, list):
            first = images[0]
            if isinstance(first, dict):
                thumbnail = first.get("url", first.get("pictureUrl", first.get("thumbnailUrl", "")))
            elif isinstance(first, str):
                thumbnail = first

    return {
        "listing_id": str(item.get("id", item.get("listingId", ""))),
        "name": item.get("name", item.get("title", "Unknown")),
        "url": item.get("url", item.get("listingUrl", "")),
        "location": item.get("location", item.get("city", "")),
        "price_per_night": price,
        "currency": item.get("currency", "EUR"),
        "bedrooms": item.get("bedrooms", 0),
        "max_guests": item.get("maxGuests", item.get("personCapacity", 0)),
        "rating": rating,
        "reviews_count": item.get("reviewsCount", item.get("numberOfReviews", 0)),
        "thumbnail": thumbnail,
    }


def get_availability_calendar(listing_urls: list[str]) -> list[dict]:
    """Fetch availability calendar for given listing URLs.

    Returns raw dataset items from the Apify actor.
    Each item contains calendar data for one listing.
    """
    client = _get_client()

    run_input = {
        "startUrls": [{"url": url} for url in listing_urls],
    }

    run = client.actor(CALENDAR_ACTOR_ID).call(run_input=run_input)

    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append(item)
    return results


def parse_calendar_data(calendar_item: dict) -> tuple[list[dict], list[dict]]:
    """Parse a calendar item into price records and availability records.

    Returns (prices, availability) where each is a list of dicts with 'date' key.
    Handles multiple possible response formats from different Apify actors.
    """
    prices = []
    availability = []

    # Try different possible structures from Apify calendar actors
    calendar_days = (
        calendar_item.get("calendar", [])
        or calendar_item.get("calendarDays", [])
        or calendar_item.get("days", [])
        or calendar_item.get("availability", [])
    )

    for day in calendar_days:
        day_date = day.get("date", day.get("day", ""))
        if not day_date:
            continue

        # Availability
        is_available = day.get("available", day.get("isAvailable", day.get("status") == "available"))
        availability.append({
            "date": day_date,
            "is_available": bool(is_available),
        })

        # Price
        price = day.get("price", day.get("pricePerNight", day.get("nightlyPrice")))
        if price is not None:
            # Handle price as dict (e.g., {"amount": 150, "currency": "EUR"})
            if isinstance(price, dict):
                price_val = price.get("amount", price.get("value"))
                currency = price.get("currency", "EUR")
            else:
                price_val = price
                currency = day.get("currency", calendar_item.get("currency", "EUR"))

            prices.append({
                "date": day_date,
                "price": float(price_val) if price_val else None,
                "currency": currency,
                "min_nights": day.get("minNights", day.get("minimumNights")),
            })

    return prices, availability
