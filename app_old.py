"""Airbnb Competitor Monitor — Home page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import logging

import pandas as pd
import streamlit as st

from db.models import init_db
from db.queries import (
    get_my_properties,
    get_competitors,
    get_latest_prices,
    get_availability,
    get_last_scrape_time,
)
from collector.data_processor import collect_all, collect_single
from collector.scheduler import start_scheduler, get_next_run
from config import APIFY_TOKEN

# Setup
logging.basicConfig(level=logging.INFO)
init_db()

st.set_page_config(
    page_title="Airbnb Monitor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Start background scheduler
if APIFY_TOKEN:
    start_scheduler()

# ── Header ──────────────────────────────────────────────────

st.title("🏠 Airbnb Competitor Monitor")
st.caption("Monitora prezzi e disponibilità dei competitor per Ca'Mugo e Ca'Mirto")

# ── Status bar ──────────────────────────────────────────────

col1, col2, col3 = st.columns(3)

with col1:
    last_scrape = get_last_scrape_time()
    if last_scrape:
        st.metric("Ultimo aggiornamento", last_scrape[:16].replace("T", " "))
    else:
        st.metric("Ultimo aggiornamento", "Mai")

with col2:
    next_run = get_next_run()
    if next_run:
        st.metric("Prossimo scraping", next_run.strftime("%H:%M"))
    else:
        st.metric("Prossimo scraping", "Non schedulato")

with col3:
    if not APIFY_TOKEN:
        st.error("⚠️ APIFY_TOKEN mancante")
    else:
        st.success("✅ API configurata")

st.divider()

# ── Property overview ───────────────────────────────────────

properties = get_my_properties()

for prop in properties:
    st.subheader(f"{'🏔️' if 'Mugo' in prop['name'] else '🏖️'} {prop['name']}")

    competitors = get_competitors(prop["id"])
    n_comps = len(competitors)

    if n_comps == 0:
        st.info("Nessun competitor monitorato. Vai a **Gestione Competitor** per aggiungerne.")
        continue

    comp_ids = [c["id"] for c in competitors]

    # Quick stats
    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.metric("Competitor", n_comps)

    # Price stats
    price_df = get_latest_prices(comp_ids)
    if not price_df.empty:
        price_df["date"] = pd.to_datetime(price_df["date"])
        today = pd.Timestamp.today().normalize()
        upcoming = price_df[
            (price_df["date"] >= today)
            & (price_df["date"] <= today + pd.Timedelta(days=7))
        ]

        with metric_cols[1]:
            if not upcoming.empty:
                avg_price = upcoming["price"].mean()
                st.metric("Prezzo medio (7gg)", f"€{avg_price:.0f}")
            else:
                st.metric("Prezzo medio (7gg)", "N/D")

        with metric_cols[2]:
            if not upcoming.empty:
                min_price = upcoming.groupby("competitor_name")["price"].mean().min()
                max_price = upcoming.groupby("competitor_name")["price"].mean().max()
                st.metric("Range prezzi", f"€{min_price:.0f} - €{max_price:.0f}")
            else:
                st.metric("Range prezzi", "N/D")
    else:
        with metric_cols[1]:
            st.metric("Prezzo medio (7gg)", "N/D")
        with metric_cols[2]:
            st.metric("Range prezzi", "N/D")

    # Availability stats
    from datetime import date, timedelta

    avail_df = get_availability(comp_ids, date_from=date.today(), date_to=date.today() + timedelta(days=30))
    with metric_cols[3]:
        if not avail_df.empty:
            occ_rate = ((1 - avail_df["is_available"].mean()) * 100)
            st.metric("Occupazione (30gg)", f"{occ_rate:.0f}%")
        else:
            st.metric("Occupazione (30gg)", "N/D")

    st.divider()

# ── Manual scraping ─────────────────────────────────────────

st.subheader("⚡ Azioni rapide")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Lancia raccolta dati ora", disabled=not APIFY_TOKEN):
        with st.spinner("Raccolta dati in corso... (può richiedere qualche minuto)"):
            try:
                updated, errors = collect_all()
                st.success(f"Completato! {updated} competitor aggiornati, {errors} errori.")
            except Exception as e:
                st.error(f"Errore: {e}")

with col2:
    st.page_link("pages/3_Gestione_Competitor.py", label="➕ Aggiungi competitor", icon="🔍")

# ── Setup instructions ──────────────────────────────────────

if not APIFY_TOKEN:
    st.divider()
    st.subheader("🔧 Setup iniziale")
    st.markdown("""
    1. Crea un account su [Apify](https://apify.com) (free tier disponibile)
    2. Vai su **Settings → API & Integrations** e crea un API token
    3. Imposta la variabile d'ambiente:
       ```bash
       export APIFY_TOKEN="apify_api_xxxxx"
       ```
    4. Riavvia la dashboard:
       ```bash
       streamlit run app.py
       ```
    """)
