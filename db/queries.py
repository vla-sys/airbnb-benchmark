"""Database query helpers."""

import sqlite3
from datetime import date, datetime
from typing import Optional

import pandas as pd

from db.models import get_connection


# ── Properties ──────────────────────────────────────────────


def get_my_properties() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM my_properties").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Competitors ─────────────────────────────────────────────


def add_competitor(
    my_property_id: int,
    airbnb_listing_id: str,
    name: str,
    airbnb_url: str,
    location: str = "",
    bedrooms: int = 0,
    max_guests: int = 0,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO competitors
           (my_property_id, airbnb_listing_id, name, airbnb_url, location, bedrooms, max_guests)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (my_property_id, airbnb_listing_id, name, airbnb_url, location, bedrooms, max_guests),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_competitors(my_property_id: int, active_only: bool = True) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM competitors WHERE my_property_id = ?"
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY name"
    rows = conn.execute(query, (my_property_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_competitor(competitor_id: int, is_active: bool):
    conn = get_connection()
    conn.execute(
        "UPDATE competitors SET is_active = ? WHERE id = ?",
        (int(is_active), competitor_id),
    )
    conn.commit()
    conn.close()


def competitor_exists(my_property_id: int, airbnb_listing_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM competitors WHERE my_property_id = ? AND airbnb_listing_id = ?",
        (my_property_id, airbnb_listing_id),
    ).fetchone()
    conn.close()
    return row is not None


# ── Price History ───────────────────────────────────────────


def save_prices(competitor_id: int, prices: list[dict]):
    """Save price records. Each dict: {date, price, currency, min_nights}."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.executemany(
        """INSERT OR IGNORE INTO price_history
           (competitor_id, date, price, currency, min_nights, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (
                competitor_id,
                p["date"],
                p.get("price"),
                p.get("currency", "EUR"),
                p.get("min_nights"),
                now,
            )
            for p in prices
        ],
    )
    conn.commit()
    conn.close()


def get_price_history(
    competitor_ids: list[int],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Get price history as a DataFrame."""
    conn = get_connection()
    placeholders = ",".join("?" * len(competitor_ids))
    query = f"""
        SELECT ph.date, ph.price, ph.min_nights, ph.scraped_at,
               c.name as competitor_name, c.id as competitor_id
        FROM price_history ph
        JOIN competitors c ON c.id = ph.competitor_id
        WHERE ph.competitor_id IN ({placeholders})
    """
    params = list(competitor_ids)

    if date_from:
        query += " AND ph.date >= ?"
        params.append(date_from.isoformat())
    if date_to:
        query += " AND ph.date <= ?"
        params.append(date_to.isoformat())

    query += " ORDER BY ph.date, c.name"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_latest_prices(competitor_ids: list[int]) -> pd.DataFrame:
    """Get the most recent price snapshot for each competitor/date."""
    conn = get_connection()
    placeholders = ",".join("?" * len(competitor_ids))
    query = f"""
        SELECT ph.date, ph.price, ph.min_nights,
               c.name as competitor_name, c.id as competitor_id
        FROM price_history ph
        JOIN competitors c ON c.id = ph.competitor_id
        WHERE ph.competitor_id IN ({placeholders})
          AND ph.scraped_at = (
              SELECT MAX(ph2.scraped_at)
              FROM price_history ph2
              WHERE ph2.competitor_id = ph.competitor_id AND ph2.date = ph.date
          )
        ORDER BY ph.date, c.name
    """
    df = pd.read_sql_query(query, conn, params=list(competitor_ids))
    conn.close()
    return df


# ── Availability History ────────────────────────────────────


def save_availability(competitor_id: int, availability: list[dict]):
    """Save availability records. Each dict: {date, is_available}."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.executemany(
        """INSERT OR IGNORE INTO availability_history
           (competitor_id, date, is_available, scraped_at)
           VALUES (?, ?, ?, ?)""",
        [
            (competitor_id, a["date"], int(a["is_available"]), now)
            for a in availability
        ],
    )
    conn.commit()
    conn.close()


def get_availability(
    competitor_ids: list[int],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Get latest availability snapshot as a DataFrame."""
    conn = get_connection()
    placeholders = ",".join("?" * len(competitor_ids))
    query = f"""
        SELECT ah.date, ah.is_available,
               c.name as competitor_name, c.id as competitor_id
        FROM availability_history ah
        JOIN competitors c ON c.id = ah.competitor_id
        WHERE ah.competitor_id IN ({placeholders})
          AND ah.scraped_at = (
              SELECT MAX(ah2.scraped_at)
              FROM availability_history ah2
              WHERE ah2.competitor_id = ah.competitor_id AND ah2.date = ah.date
          )
    """
    params = list(competitor_ids)

    if date_from:
        query += " AND ah.date >= ?"
        params.append(date_from.isoformat())
    if date_to:
        query += " AND ah.date <= ?"
        params.append(date_to.isoformat())

    query += " ORDER BY ah.date, c.name"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_last_scrape_time() -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(scraped_at) as last_scrape FROM price_history"
    ).fetchone()
    conn.close()
    return row["last_scrape"] if row else None
