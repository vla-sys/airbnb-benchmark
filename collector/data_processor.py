"""Data processing: fetches calendar data and saves to DB."""

import logging
from datetime import datetime

from collector.apify_client import get_availability_calendar, parse_calendar_data
from db.queries import get_competitors, save_prices, save_availability, get_my_properties

logger = logging.getLogger(__name__)


def collect_all():
    """Fetch calendar data for all active competitors and save to DB."""
    properties = get_my_properties()
    total_competitors = 0
    total_errors = 0

    for prop in properties:
        competitors = get_competitors(prop["id"], active_only=True)
        if not competitors:
            logger.info(f"No active competitors for {prop['name']}, skipping.")
            continue

        logger.info(f"Collecting data for {prop['name']}: {len(competitors)} competitors")

        # Batch listing URLs
        url_to_competitor = {}
        for comp in competitors:
            url = comp["airbnb_url"]
            if url:
                url_to_competitor[url] = comp

        if not url_to_competitor:
            continue

        try:
            calendar_results = get_availability_calendar(list(url_to_competitor.keys()))
        except Exception as e:
            logger.error(f"Apify call failed for {prop['name']}: {e}")
            total_errors += len(url_to_competitor)
            continue

        # Match results back to competitors
        for cal_item in calendar_results:
            listing_url = cal_item.get("url", cal_item.get("listingUrl", ""))

            # Find matching competitor
            comp = None
            for url, c in url_to_competitor.items():
                if url in listing_url or listing_url in url:
                    comp = c
                    break

            if not comp:
                # Try matching by listing ID
                listing_id = str(cal_item.get("id", cal_item.get("listingId", "")))
                for c in competitors:
                    if c["airbnb_listing_id"] == listing_id:
                        comp = c
                        break

            if not comp:
                logger.warning(f"Could not match calendar result to competitor: {listing_url}")
                continue

            try:
                prices, availability = parse_calendar_data(cal_item)
                if prices:
                    save_prices(comp["id"], prices)
                if availability:
                    save_availability(comp["id"], availability)
                total_competitors += 1
                logger.info(f"  Saved {len(prices)} price records, {len(availability)} availability records for {comp['name']}")
            except Exception as e:
                logger.error(f"  Error processing {comp['name']}: {e}")
                total_errors += 1

    logger.info(
        f"Collection complete: {total_competitors} competitors updated, {total_errors} errors"
    )
    return total_competitors, total_errors


def collect_single(competitor_id: int):
    """Fetch calendar data for a single competitor."""
    from db.models import get_connection

    conn = get_connection()
    row = conn.execute("SELECT * FROM competitors WHERE id = ?", (competitor_id,)).fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Competitor {competitor_id} not found")

    comp = dict(row)
    url = comp["airbnb_url"]
    if not url:
        raise ValueError(f"Competitor {comp['name']} has no URL")

    results = get_availability_calendar([url])
    if not results:
        logger.warning(f"No calendar data returned for {comp['name']}")
        return 0, 0

    cal_item = results[0]
    prices, availability = parse_calendar_data(cal_item)

    if prices:
        save_prices(comp["id"], prices)
    if availability:
        save_availability(comp["id"], availability)

    return len(prices), len(availability)
