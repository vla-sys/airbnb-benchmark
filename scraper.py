"""Airbnb calendar & pricing scraper using the internal GraphQL API."""

import base64
import json
import re
from datetime import date, timedelta, datetime
from typing import Optional

import requests

API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
CALENDAR_HASH = "b23335819df0dc391a338d665e2ee2f5d3bff19181d05c0b39bc6c5aac403914"
PDP_SECTIONS_HASH = "f4bdd45a5c3b45d038ed02b058f2ad0479a218723b0abcef2499854d8f4f1b4f"
BASE_URL = f"https://www.airbnb.com/api/v3/PdpAvailabilityCalendar/{CALENDAR_HASH}"
PDP_SECTIONS_URL = f"https://www.airbnb.com/api/v3/StaysPdpSections/{PDP_SECTIONS_HASH}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "X-Airbnb-Api-Key": API_KEY,
}


def extract_listing_id(url: str) -> str:
    """Extract numeric listing ID from an Airbnb URL."""
    match = re.search(r"/rooms/(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Cannot extract listing ID from: {url}")


def fetch_calendar(listing_id: str, start_month: int, start_year: int, count: int = 4) -> list[dict]:
    """Fetch calendar data for a listing.

    Returns a flat list of day dicts with keys:
        date, available, minNights, maxNights, availableForCheckin, availableForCheckout, bookable
    """
    params = {
        "operationName": "PdpAvailabilityCalendar",
        "locale": "en",
        "currency": "EUR",
        "variables": json.dumps({
            "request": {
                "count": count,
                "listingId": listing_id,
                "month": start_month,
                "year": start_year,
            }
        }),
        "extensions": json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": CALENDAR_HASH,
            }
        }),
    }

    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    data = resp.json()
    months = (
        data.get("data", {})
        .get("merlin", {})
        .get("pdpAvailabilityCalendar", {})
        .get("calendarMonths", [])
    )

    days = []
    for month in months:
        for day in month.get("days", []):
            days.append({
                "date": day["calendarDate"],
                "available": day["available"],
                "minNights": day.get("minNights", 1),
                "maxNights": day.get("maxNights"),
                "checkin": day.get("availableForCheckin", False),
                "checkout": day.get("availableForCheckout", False),
                "bookable": day.get("bookable", False),
            })
    return days


def _b64_id(prefix: str, listing_id: str) -> str:
    """Encode listing ID as Airbnb's base64 format."""
    return base64.b64encode(f"{prefix}:{listing_id}".encode()).decode()


def fetch_price_for_stay(listing_id: str, check_in: str, check_out: str) -> Optional[dict]:
    """Fetch the total and nightly price for a specific stay via GraphQL API.

    Returns dict with keys: total, nightly, nights, currency
    or None if unavailable.
    """
    d_in = datetime.strptime(check_in, "%Y-%m-%d").date()
    d_out = datetime.strptime(check_out, "%Y-%m-%d").date()
    nights = (d_out - d_in).days

    imp = "p3_1700000000_scraper"
    variables = {
        "id": _b64_id("StayListing", listing_id),
        "demandStayListingId": _b64_id("DemandStayListing", listing_id),
        "pdpSectionsRequest": {
            "adults": "1",
            "amenityFilters": None,
            "bypassTargetings": False,
            "categoryTag": None,
            "causeId": None,
            "children": None,
            "disasterId": None,
            "discountedGuestFeeVersion": None,
            "federatedSearchId": None,
            "forceBoostPriorityMessageType": None,
            "hostPreview": False,
            "infants": None,
            "interactionType": None,
            "layouts": ["SIDEBAR", "SINGLE_COLUMN"],
            "pets": 0,
            "pdpTypeOverride": None,
            "photoId": None,
            "preview": False,
            "previousStateCheckIn": None,
            "previousStateCheckOut": None,
            "priceDropSource": None,
            "privateBooking": False,
            "promotionUuid": None,
            "relaxedAmenityIds": None,
            "searchId": None,
            "selectedCancellationPolicyId": None,
            "selectedRatePlanId": None,
            "splitStays": None,
            "staysBookingMigrationEnabled": False,
            "translateUgc": None,
            "useNewSectionWrapperApi": False,
            "sectionIds": ["BOOK_IT_SIDEBAR"],
            "checkIn": check_in,
            "checkOut": check_out,
            "p3ImpressionId": imp,
        },
        "categoryTag": None,
        "federatedSearchId": None,
        "p3ImpressionId": imp,
        "photoId": None,
        "checkIn": check_in,
        "checkOut": check_out,
        "includePdpMigrationAmenitiesFragment": False,
        "includeGpAmenitiesFragment": True,
        "includePdpMigrationDescriptionFragment": False,
        "includeGpDescriptionFragment": True,
        "includePdpMigrationHeroFragment": False,
        "includeGpHeroFragment": True,
        "includePdpMigrationHighlightsFragment": False,
        "includeGpHighlightsFragment": True,
        "includePdpMigrationMeetYourHostFragment": False,
        "includeGpMeetYourHostFragment": True,
        "includePdpMigrationNavFragment": False,
        "includeGpNavFragment": True,
        "includePdpMigrationNavMobileFragment": False,
        "includeGpNavMobileFragment": True,
        "includePdpMigrationBookItNonExperiencedGuestFragment": False,
        "includeGpBookItNonExperiencedGuestFragment": True,
        "includePdpMigrationOverviewV2Fragment": False,
        "includeGpOverviewV2Fragment": True,
        "includePdpMigrationReviewsHighlightBannerFragment": False,
        "includeGpReviewsHighlightBannerFragment": True,
        "includeGpNonExperiencedGuestLearnMoreModalFragment": True,
        "includePdpMigrationReportToAirbnbFragment": False,
        "includeGpReportToAirbnbFragment": True,
        "includePdpMigrationReviewsFragment": False,
        "includeGpReviewsFragment": True,
        "includePdpMigrationReviewsEmptyFragment": False,
        "includeGpReviewsEmptyFragment": True,
        "includePdpMigrationTitleFragment": False,
        "includeGpTitleFragment": True,
        "includePdpMigrationPoliciesFragment": False,
        "includeGpPoliciesFragment": True,
    }

    params = {
        "operationName": "StaysPdpSections",
        "locale": "en",
        "currency": "EUR",
        "variables": json.dumps(variables),
        "extensions": json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": PDP_SECTIONS_HASH,
            }
        }),
    }

    try:
        resp = requests.get(PDP_SECTIONS_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("errors"):
            return None

        body_str = json.dumps(data, ensure_ascii=False)

        # Extract total price from structuredDisplayPrice
        total = _extract_total_price(body_str)
        if total is None:
            return None

        return {
            "total": total,
            "nightly": round(total / nights, 2) if nights > 0 else total,
            "nights": nights,
            "currency": "EUR",
        }
    except Exception:
        return None


def _parse_price_str(price_str: str) -> Optional[float]:
    """Parse a formatted price string like '€ 2,259' or '€ 450.14' into a float."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[€$£\s\xa0]", "", price_str)
    if not cleaned:
        return None
    # Handle European formatting: "2.259,19" vs US: "2,259.19"
    # If it has both . and , check which is the decimal separator
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # European: 2.259,19 -> 2259.19
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US: 2,259.19 -> 2259.19
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be thousands separator (2,259) or decimal (3,50)
        parts = cleaned.split(",")
        if len(parts[-1]) == 3:
            # Thousands separator: 2,259
            cleaned = cleaned.replace(",", "")
        else:
            # Decimal: 3,50
            cleaned = cleaned.replace(",", ".")
    # "." only is fine as-is
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_total_price(body_str: str) -> Optional[float]:
    """Extract total price from a StaysPdpSections API response."""
    # Best source: nightly price from breakdown "5 nights x € 450.14"
    nightly_match = re.search(
        r'"description":\s*"(\d+)\s*nights?\s*x\s*([^"]+)"',
        body_str,
    )
    if nightly_match:
        nights = int(nightly_match.group(1))
        nightly_price = _parse_price_str(nightly_match.group(2))
        if nightly_price and nights > 0:
            return round(nightly_price * nights, 2)

    # Fallback: total from structuredDisplayPrice
    total_match = re.search(
        r'"structuredDisplayPrice".*?"primaryLine".*?"price":\s*"([^"]+)"',
        body_str,
    )
    if total_match:
        return _parse_price_str(total_match.group(1))

    return None


def build_stay_windows(days: list[dict]) -> list[dict]:
    """Build check-in/check-out windows covering available days.

    For each available check-in day, creates a stay of minNights duration.
    Returns list of dicts: {check_in, check_out, minNights}
    """
    windows = []
    day_map = {d["date"]: d for d in days}
    today = date.today()

    for day in days:
        d = date.fromisoformat(day["date"])
        if d <= today:
            continue
        if not day["checkin"] or not day["available"]:
            continue

        min_n = day["minNights"]
        checkout_date = d + timedelta(days=min_n)
        co_str = checkout_date.isoformat()

        # Verify checkout date is valid
        co_day = day_map.get(co_str)
        if co_day and co_day["checkout"]:
            windows.append({
                "check_in": day["date"],
                "check_out": co_str,
                "minNights": min_n,
            })

    return windows


def fetch_prices_for_windows(listing_id: str, windows: list[dict], max_calls: int = 25) -> list[dict]:
    """Fetch prices for a subset of stay windows.

    To minimize API calls, samples evenly across the date range.
    Returns windows enriched with 'price' dict.
    """
    if len(windows) <= max_calls:
        selected = windows
    else:
        step = len(windows) / max_calls
        selected = [windows[int(i * step)] for i in range(max_calls)]

    results = []
    for w in selected:
        price = fetch_price_for_stay(listing_id, w["check_in"], w["check_out"])
        entry = {**w, "price": price}
        results.append(entry)

    return results


def interpolate_daily_prices(calendar_days: list[dict], priced_windows: list[dict]) -> list[dict]:
    """Assign a nightly price to each calendar day by interpolating from priced windows.

    Each day gets the nightly price from the closest priced window that covers it.
    """
    # Build a map: date -> nightly price
    price_map = {}
    for w in priced_windows:
        if not w.get("price"):
            continue
        nightly = w["price"]["nightly"]
        d = date.fromisoformat(w["check_in"])
        end = date.fromisoformat(w["check_out"])
        while d < end:
            price_map[d.isoformat()] = nightly
            d += timedelta(days=1)

    # Assign prices to calendar days
    enriched = []
    for day in calendar_days:
        day_copy = {**day}
        day_copy["nightly_price"] = price_map.get(day["date"])
        enriched.append(day_copy)

    # Forward fill for gaps (including unavailable days — show estimated price)
    last_price = None
    for day in enriched:
        if day["nightly_price"] is not None:
            last_price = day["nightly_price"]
        elif last_price is not None:
            day["nightly_price"] = last_price

    # Backward fill for days before first priced window
    last_price = None
    for day in reversed(enriched):
        if day["nightly_price"] is not None:
            last_price = day["nightly_price"]
        elif last_price is not None:
            day["nightly_price"] = last_price

    return enriched


if __name__ == "__main__":
    # Quick test
    listing_id = "31351271"
    today = date.today()

    print(f"Fetching calendar for listing {listing_id}...")
    days = fetch_calendar(listing_id, today.month, today.year, count=4)
    print(f"Got {len(days)} days")

    print(f"\nBuilding stay windows...")
    windows = build_stay_windows(days)
    print(f"Got {len(windows)} possible check-in windows")

    print(f"\nFetching prices for sample windows...")
    priced = fetch_prices_for_windows(listing_id, windows, max_calls=5)
    for p in priced:
        price_str = f"€{p['price']['nightly']}/night (€{p['price']['total']} total)" if p.get("price") else "N/A"
        print(f"  {p['check_in']} -> {p['check_out']} ({p['minNights']}n): {price_str}")

    print(f"\nInterpolating daily prices...")
    enriched = interpolate_daily_prices(days, priced)
    avail_with_price = [d for d in enriched if d["available"] and d.get("nightly_price")]
    print(f"Days with prices: {len(avail_with_price)} / {len([d for d in enriched if d['available']])}")
