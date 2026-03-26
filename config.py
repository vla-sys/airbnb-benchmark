import os
from pathlib import Path

# Apify API token — reads from Streamlit secrets (cloud) or env var (local)
def _get_apify_token():
    try:
        import streamlit as st
        return st.secrets.get("APIFY_TOKEN", os.environ.get("APIFY_TOKEN", ""))
    except Exception:
        return os.environ.get("APIFY_TOKEN", "")

APIFY_TOKEN = _get_apify_token()

# Apify actor IDs
SEARCH_ACTOR_ID = "tri_angle/airbnb-scraper"
CALENDAR_ACTOR_ID = "rigelbytes/airbnb-availability-calendar"

# Database
DB_DIR = Path(__file__).parent / "db"
DB_PATH = DB_DIR / "monitor.db"

# Scheduler
SCRAPE_HOUR = 6  # Run daily at 6 AM
SCRAPE_MINUTE = 0

# Your properties (pre-seeded)
MY_PROPERTIES = [
    {
        "name": "Ca'Mugo",
        "airbnb_url": "https://airbnb.com/h/ca-mugo",
        "location": "Borca di Cadore, Dolomites",
        "latitude": 46.4372,
        "longitude": 12.2108,
        "bedrooms": 3,
        "max_guests": 6,
    },
    {
        "name": "Ca'Mirto",
        "airbnb_url": "https://airbnb.com/h/camirto-sardinia",
        "location": "San Teodoro, Sardinia",
        "latitude": 40.7697,
        "longitude": 9.6731,
        "bedrooms": 4,
        "max_guests": 9,
    },
]
