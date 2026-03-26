"""SQLite database schema and initialization."""

import sqlite3
from pathlib import Path

from config import DB_PATH, MY_PROPERTIES

SCHEMA = """
CREATE TABLE IF NOT EXISTS my_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    airbnb_url TEXT,
    location TEXT,
    latitude REAL,
    longitude REAL,
    bedrooms INTEGER,
    max_guests INTEGER
);

CREATE TABLE IF NOT EXISTS competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    my_property_id INTEGER REFERENCES my_properties(id),
    airbnb_listing_id TEXT NOT NULL,
    name TEXT,
    airbnb_url TEXT,
    location TEXT,
    bedrooms INTEGER,
    max_guests INTEGER,
    is_active BOOLEAN DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id INTEGER REFERENCES competitors(id),
    date DATE NOT NULL,
    price REAL,
    currency TEXT DEFAULT 'EUR',
    min_nights INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS availability_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id INTEGER REFERENCES competitors(id),
    date DATE NOT NULL,
    is_available BOOLEAN,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_competitor_date
    ON price_history(competitor_id, date);
CREATE INDEX IF NOT EXISTS idx_avail_competitor_date
    ON availability_history(competitor_id, date);
CREATE INDEX IF NOT EXISTS idx_competitors_property
    ON competitors(my_property_id, is_active);
"""


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed properties if needed."""
    conn = get_connection()
    conn.executescript(SCHEMA)

    # Seed properties if empty
    count = conn.execute("SELECT COUNT(*) FROM my_properties").fetchone()[0]
    if count == 0:
        for prop in MY_PROPERTIES:
            conn.execute(
                """INSERT INTO my_properties
                   (name, airbnb_url, location, latitude, longitude, bedrooms, max_guests)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    prop["name"],
                    prop["airbnb_url"],
                    prop["location"],
                    prop["latitude"],
                    prop["longitude"],
                    prop["bedrooms"],
                    prop["max_guests"],
                ),
            )
        conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
