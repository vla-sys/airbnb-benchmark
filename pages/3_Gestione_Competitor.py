"""Competitor management page — search, add, toggle competitors."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from db.models import init_db
from db.queries import (
    get_my_properties,
    get_competitors,
    add_competitor,
    toggle_competitor,
    competitor_exists,
)
from collector.apify_client import search_listings
from config import APIFY_TOKEN

init_db()

st.set_page_config(page_title="Gestione Competitor", page_icon="🔍", layout="wide")
st.title("🔍 Gestione Competitor")

# ── Property selector ───────────────────────────────────────

properties = get_my_properties()
prop_names = [p["name"] for p in properties]
selected_name = st.selectbox("Property", prop_names)
selected_prop = next(p for p in properties if p["name"] == selected_name)

st.divider()

# ── Current competitors ─────────────────────────────────────

st.subheader(f"Competitor monitorati per {selected_name}")

competitors = get_competitors(selected_prop["id"], active_only=False)

if competitors:
    for comp in competitors:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            st.markdown(f"**{comp['name']}**")
            if comp["airbnb_url"]:
                st.caption(comp["airbnb_url"])
        with col2:
            st.caption(f"{comp['bedrooms']} camere · {comp['max_guests']} ospiti")
        with col3:
            status = "✅ Attivo" if comp["is_active"] else "⏸️ Pausa"
            st.caption(status)
        with col4:
            if comp["is_active"]:
                if st.button("Disattiva", key=f"deact_{comp['id']}"):
                    toggle_competitor(comp["id"], False)
                    st.rerun()
            else:
                if st.button("Riattiva", key=f"react_{comp['id']}"):
                    toggle_competitor(comp["id"], True)
                    st.rerun()
else:
    st.info("Nessun competitor monitorato. Usa la ricerca qui sotto per aggiungerne.")

st.divider()

# ── Search for new competitors ──────────────────────────────

st.subheader("Cerca nuovi competitor")

if not APIFY_TOKEN:
    st.warning(
        "⚠️ APIFY_TOKEN non configurato. "
        "Imposta la variabile d'ambiente `APIFY_TOKEN` o aggiornala in `config.py`."
    )

with st.form("search_form"):
    col1, col2 = st.columns(2)
    with col1:
        radius_km = st.select_slider(
            "📍 Raggio di ricerca",
            options=[5, 10, 15, 20, 25, 30, 40, 50],
            value=20,
            help="Distanza in km dal tuo listing",
        )
        min_bedrooms = st.number_input(
            "Camere minime", min_value=0, max_value=10, value=max(0, selected_prop["bedrooms"] - 1)
        )
    with col2:
        max_guests = st.number_input(
            "Ospiti minimi", min_value=0, max_value=20, value=max(0, selected_prop["max_guests"] - 2)
        )
        max_results = st.number_input(
            "Risultati max", min_value=5, max_value=100, value=20
        )

    st.caption(
        f"🗺️ Cercherà entro **{radius_km} km** da {selected_prop['location']} "
        f"(lat {selected_prop['latitude']}, lng {selected_prop['longitude']})"
    )

    submitted = st.form_submit_button("🔍 Cerca su Airbnb", disabled=not APIFY_TOKEN)

if submitted and APIFY_TOKEN:
    with st.spinner("Ricerca in corso su Airbnb tramite Apify..."):
        try:
            results = search_listings(
                latitude=selected_prop["latitude"],
                longitude=selected_prop["longitude"],
                radius_km=radius_km,
                location=selected_prop["location"],
                min_bedrooms=min_bedrooms,
                max_guests=max_guests,
                max_results=max_results,
            )
            st.session_state["search_results"] = results
        except Exception as e:
            st.error(f"Errore nella ricerca: {e}")
            st.session_state["search_results"] = []

# ── Display search results ──────────────────────────────────

if "search_results" in st.session_state and st.session_state["search_results"]:
    results = st.session_state["search_results"]
    st.subheader(f"Risultati: {len(results)} listing trovati")

    for i, listing in enumerate(results):
        already_added = competitor_exists(selected_prop["id"], listing["listing_id"])

        with st.container():
            cols = st.columns([1, 3, 2, 1])

            # Thumbnail
            with cols[0]:
                if listing.get("thumbnail"):
                    st.image(listing["thumbnail"], width=120)
                else:
                    st.markdown("🏠")

            # Name & location
            with cols[1]:
                st.markdown(f"**{listing['name']}**")
                st.caption(f"📍 {listing['location']}")
                if listing["url"]:
                    st.caption(listing["url"])

            # Price & details
            with cols[2]:
                price_str = f"€{listing['price_per_night']:.0f}/notte" if listing["price_per_night"] else "N/D"
                st.metric("Prezzo", price_str)
                st.caption(
                    f"{listing['bedrooms']} camere · {listing['max_guests']} ospiti · "
                    f"⭐ {listing['rating'] or 'N/D'} ({listing['reviews_count']} rec.)"
                )

            # Action
            with cols[3]:
                if already_added:
                    st.success("✓ Aggiunto")
                else:
                    if st.button("➕ Aggiungi", key=f"add_{i}"):
                        add_competitor(
                            my_property_id=selected_prop["id"],
                            airbnb_listing_id=listing["listing_id"],
                            name=listing["name"],
                            airbnb_url=listing["url"],
                            location=listing["location"],
                            bedrooms=listing["bedrooms"],
                            max_guests=listing["max_guests"],
                        )
                        st.rerun()
            st.divider()

# ── Manual add ──────────────────────────────────────────────

st.subheader("Aggiungi manualmente")
st.caption("Se conosci già l'URL di un competitor, puoi aggiungerlo direttamente.")

with st.form("manual_add"):
    m_name = st.text_input("Nome listing")
    m_url = st.text_input("URL Airbnb", placeholder="https://www.airbnb.com/rooms/12345678")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        m_bedrooms = st.number_input("Camere", min_value=0, max_value=20, value=0)
    with m_col2:
        m_guests = st.number_input("Ospiti max", min_value=0, max_value=30, value=0)

    if st.form_submit_button("➕ Aggiungi competitor"):
        if m_name and m_url:
            # Extract listing ID from URL
            listing_id = m_url.rstrip("/").split("/")[-1].split("?")[0]
            add_competitor(
                my_property_id=selected_prop["id"],
                airbnb_listing_id=listing_id,
                name=m_name,
                airbnb_url=m_url,
                location="",
                bedrooms=m_bedrooms,
                max_guests=m_guests,
            )
            st.success(f"✓ {m_name} aggiunto!")
            st.rerun()
        else:
            st.warning("Inserisci almeno nome e URL.")
