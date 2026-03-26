"""Airbnb Pricing Calendar — Benchmark vs Competitor"""

import calendar as cal_mod
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import streamlit as st

from scraper import (
    extract_listing_id,
    fetch_calendar,
    build_stay_windows,
    fetch_prices_for_windows,
    interpolate_daily_prices,
)

# ── Config ─────────────────────────────────────────────────

BENCHMARK = {
    "name": "Ca'Mugo",
    "listing_id": "1363939812329907610",
}

SAVED_FILE = Path(__file__).parent / "saved_competitors.json"

# ── Page config ────────────────────────────────────────────

st.set_page_config(
    page_title="Airbnb Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

# Hide default menu, footer, and sidebar toggle
st.markdown("""
<style>
    /* Hide hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarCollapsedControl"] {display: none;}

    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Smooth scrolling */
    html { scroll-behavior: smooth; }

    /* Custom metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        font-size: 12px !important;
        font-weight: 500 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }

    /* Button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: none;
        border-radius: 10px;
        padding: 12px 28px;
        font-weight: 600;
        letter-spacing: 0.02em;
        box-shadow: 0 2px 8px rgba(37,99,235,0.3);
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(37,99,235,0.4);
        transform: translateY(-1px);
    }

    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 12px 16px;
        font-size: 15px;
        transition: border-color 0.2s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        border-radius: 10px;
    }

    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #e2e8f0, transparent);
        margin: 24px 0;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ── Saved competitors ──────────────────────────────────────

def _load_saved() -> list[dict]:
    if SAVED_FILE.exists():
        return json.loads(SAVED_FILE.read_text())
    return []


def _save_competitors(comps: list[dict]):
    SAVED_FILE.write_text(json.dumps(comps, indent=2))


def _add_competitor(name: str, url: str):
    comps = _load_saved()
    listing_id = extract_listing_id(url)
    if not any(c["listing_id"] == listing_id for c in comps):
        comps.append({"name": name, "url": url, "listing_id": listing_id})
        _save_competitors(comps)


def _remove_competitor(listing_id: str):
    comps = [c for c in _load_saved() if c["listing_id"] != listing_id]
    _save_competitors(comps)


# ── Header ─────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
    <div style="background:linear-gradient(135deg,#2563eb,#7c3aed);width:48px;height:48px;
                border-radius:12px;display:flex;align-items:center;justify-content:center;
                font-size:24px;box-shadow:0 4px 12px rgba(37,99,235,0.3);">📊</div>
    <div>
        <h1 style="margin:0;font-size:32px;font-weight:700;color:#1e293b;letter-spacing:-0.02em;">
            Airbnb Benchmark</h1>
        <p style="margin:0;font-size:15px;color:#64748b;">
            Confronta <strong style="color:#2563eb;">Ca'Mugo</strong> con i competitor — prezzi, disponibilità e soggiorno minimo</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Competitor selection ───────────────────────────────────

saved = _load_saved()

tab_saved, tab_new, tab_manage = st.tabs(["Competitor salvati", "Nuovo URL", "Gestisci lista"])

with tab_saved:
    if saved:
        options = {f"{c['name']}  —  {c['listing_id']}": c for c in saved}
        selected_label = st.selectbox(
            "Scegli un competitor salvato",
            list(options.keys()),
            label_visibility="collapsed",
        )
        selected_comp = options[selected_label]
        comp_url_to_use = selected_comp["url"]
    else:
        st.info("Nessun competitor salvato. Usa la tab **Nuovo URL** per aggiungerne uno.")
        comp_url_to_use = None

with tab_new:
    new_url = st.text_input(
        "URL Airbnb del competitor",
        placeholder="https://www.airbnb.com/rooms/12345678",
        key="new_comp_url",
    )
    col_name, col_save = st.columns([3, 1])
    with col_name:
        new_name = st.text_input("Nome (opzionale)", placeholder="Es: Chalet Cortina", key="new_comp_name")
    with col_save:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("💾 Salva", use_container_width=True):
            if new_url:
                try:
                    lid = extract_listing_id(new_url)
                    label = new_name or f"Listing {lid}"
                    _add_competitor(label, new_url)
                    st.success(f"Salvato: {label}")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
    if new_url:
        comp_url_to_use = new_url

with tab_manage:
    if saved:
        for c in saved:
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(f"**{c['name']}** — `{c['listing_id']}`")
            with col_del:
                if st.button("🗑️", key=f"del_{c['listing_id']}", help="Rimuovi"):
                    _remove_competitor(c["listing_id"])
                    st.rerun()
    else:
        st.caption("Lista vuota.")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Launch analysis ────────────────────────────────────────

col_slider, col_btn = st.columns([3, 1])
with col_slider:
    max_price_calls = st.slider("Precisione prezzo", 5, 30, 10, help="Più alto = più preciso ma più lento")
with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    go = st.button("🔍 Confronta", type="primary", use_container_width=True)

# ── Fetch data ─────────────────────────────────────────────


def _fetch_property(listing_id: str, n_calls: int) -> dict:
    today = date.today()
    cal_days = fetch_calendar(listing_id, today.month, today.year, count=4)
    if not cal_days:
        return {"days": [], "windows": []}
    windows = build_stay_windows(cal_days)
    priced = fetch_prices_for_windows(listing_id, windows, max_calls=n_calls)
    enriched = interpolate_daily_prices(cal_days, priced)
    return {"days": enriched, "windows": priced}


if go:
    if not comp_url_to_use:
        st.warning("Seleziona o inserisci un competitor.")
        st.stop()

    try:
        comp_id = extract_listing_id(comp_url_to_use)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    progress = st.progress(0, text="Scaricamento Ca'Mugo...")
    bench_data = _fetch_property(BENCHMARK["listing_id"], max_price_calls)
    progress.progress(50, text="Scaricamento competitor...")
    comp_data = _fetch_property(comp_id, max_price_calls)
    progress.progress(100, text="Analisi completata!")

    st.session_state["bench"] = bench_data
    st.session_state["comp"] = comp_data
    st.session_state["comp_id"] = comp_id

# ── Display results ────────────────────────────────────────

if "bench" not in st.session_state:
    st.stop()

bench_data = st.session_state["bench"]
comp_data = st.session_state["comp"]

bench_days = {d["date"]: d for d in bench_data["days"]}
comp_days = {d["date"]: d for d in comp_data["days"]}
all_dates = sorted(set(list(bench_days.keys()) + list(comp_days.keys())))

# ── Summary metrics ────────────────────────────────────────

bench_prices = [d["nightly_price"] for d in bench_data["days"] if d.get("nightly_price")]
comp_prices = [d["nightly_price"] for d in comp_data["days"] if d.get("nightly_price")]
bench_avg = sum(bench_prices) / len(bench_prices) if bench_prices else 0
comp_avg = sum(comp_prices) / len(comp_prices) if comp_prices else 0
bench_avail = sum(1 for d in bench_data["days"] if d["available"])
comp_avail = sum(1 for d in comp_data["days"] if d["available"])

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ca'Mugo /notte", f"€{bench_avg:.0f}" if bench_prices else "N/D")
c2.metric("Competitor /notte", f"€{comp_avg:.0f}" if comp_prices else "N/D")
if bench_prices and comp_prices:
    diff = bench_avg - comp_avg
    pct = (diff / comp_avg) * 100 if comp_avg else 0
    c3.metric("Differenza", f"{pct:+.0f}%", delta=f"€{diff:+.0f}")
else:
    c3.metric("Differenza", "N/D")
c4.metric("Disponibilità", f"{bench_avail} vs {comp_avail}")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# Legend
st.markdown("""
<div style="display:flex;gap:24px;align-items:center;padding:12px 16px;
            background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;font-size:13px;">
    <span><strong style="color:#2563eb;">● Ca'Mugo</strong></span>
    <span><strong style="color:#dc2626;">● Competitor</strong></span>
    <span style="color:#64748b;">🔴 = occupato</span>
    <span style="background:#dbeafe;padding:2px 8px;border-radius:4px;color:#1e40af;">Ca'Mugo più economico</span>
    <span style="background:#fee2e2;padding:2px 8px;border-radius:4px;color:#991b1b;">Competitor più economico</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Calendar ───────────────────────────────────────────────

months_set: dict[tuple, list] = defaultdict(list)
for dt_str in all_dates:
    dt = date.fromisoformat(dt_str)
    months_set[(dt.year, dt.month)].append(dt_str)

today = date.today()

for (year, month), _ in sorted(months_set.items()):
    month_name = cal_mod.month_name[month]
    st.markdown(
        f'<h3 style="font-size:20px;font-weight:600;color:#1e293b;margin:24px 0 12px;">'
        f'{month_name} {year}</h3>',
        unsafe_allow_html=True,
    )

    weeks = cal_mod.monthcalendar(year, month)

    html = (
        '<table style="border-collapse:separate;border-spacing:3px;width:100%;'
        'text-align:center;font-family:Inter,sans-serif;">'
    )
    html += "<tr>"
    for hdr in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
        html += (
            f'<th style="padding:6px;font-size:11px;font-weight:600;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.08em;">{hdr}</th>'
        )
    html += "</tr>"

    for week in weeks:
        html += "<tr>"
        for day_num in week:
            if day_num == 0:
                html += '<td style="padding:4px;"></td>'
                continue

            dt = date(year, month, day_num)
            dt_str = dt.isoformat()
            b = bench_days.get(dt_str)
            c = comp_days.get(dt_str)

            if dt < today:
                html += f'<td style="padding:6px 2px;color:#cbd5e1;font-size:12px;">{day_num}</td>'
                continue

            # Benchmark line
            if b and not b["available"]:
                b_html = '<span style="color:#93c5fd;font-size:10px;">🔴</span>'
            elif b and b.get("nightly_price"):
                b_html = (
                    f'<span style="color:#2563eb;font-weight:600;font-size:11px;">'
                    f'€{b["nightly_price"]:.0f}</span>'
                    f'<span style="color:#93c5fd;font-size:9px;"> {b["minNights"]}n</span>'
                )
            elif b:
                b_html = '<span style="color:#93c5fd;font-size:10px;">—</span>'
            else:
                b_html = ""

            # Competitor line
            if c and not c["available"]:
                c_html = '<span style="color:#fca5a5;font-size:10px;">🔴</span>'
            elif c and c.get("nightly_price"):
                c_html = (
                    f'<span style="color:#dc2626;font-weight:600;font-size:11px;">'
                    f'€{c["nightly_price"]:.0f}</span>'
                    f'<span style="color:#fca5a5;font-size:9px;"> {c["minNights"]}n</span>'
                )
            elif c:
                c_html = '<span style="color:#fca5a5;font-size:10px;">—</span>'
            else:
                c_html = ""

            # Cell background
            cell_bg = "#ffffff"
            border_color = "#f1f5f9"
            if b and b.get("nightly_price") and c and c.get("nightly_price"):
                bp, cp = b["nightly_price"], c["nightly_price"]
                if bp < cp:
                    cell_bg = "#eff6ff"
                    border_color = "#bfdbfe"
                elif bp > cp:
                    cell_bg = "#fef2f2"
                    border_color = "#fecaca"
                else:
                    cell_bg = "#f8fafc"
                    border_color = "#e2e8f0"

            html += (
                f'<td style="padding:5px 2px;background:{cell_bg};border-radius:6px;'
                f'border:1px solid {border_color};vertical-align:top;min-width:80px;">'
                f'<div style="font-weight:700;font-size:13px;color:#334155;margin-bottom:3px;">{day_num}</div>'
                f'<div style="line-height:1.5;">{b_html}</div>'
                f'<div style="line-height:1.5;">{c_html}</div>'
                f'</td>'
            )
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Price comparison table ─────────────────────────────────
st.markdown(
    '<h3 style="font-size:20px;font-weight:600;color:#1e293b;">Dettaglio finestre di prezzo</h3>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<p style="font-size:14px;font-weight:600;color:#2563eb;margin-bottom:4px;">Ca\'Mugo</p>',
        unsafe_allow_html=True,
    )
    rows = []
    for w in bench_data["windows"]:
        if w.get("price"):
            rows.append({
                "Check-in": w["check_in"],
                "Check-out": w["check_out"],
                "Notti": w["minNights"],
                "Totale": f"€{w['price']['total']:.0f}",
                "/notte": f"€{w['price']['nightly']:.0f}",
            })
    if rows:
        st.dataframe(rows, hide_index=True, width=500)
    else:
        st.caption("Nessun dato.")

with col2:
    st.markdown(
        '<p style="font-size:14px;font-weight:600;color:#dc2626;margin-bottom:4px;">Competitor</p>',
        unsafe_allow_html=True,
    )
    rows = []
    for w in comp_data["windows"]:
        if w.get("price"):
            rows.append({
                "Check-in": w["check_in"],
                "Check-out": w["check_out"],
                "Notti": w["minNights"],
                "Totale": f"€{w['price']['total']:.0f}",
                "/notte": f"€{w['price']['nightly']:.0f}",
            })
    if rows:
        st.dataframe(rows, hide_index=True, width=500)
    else:
        st.caption("Nessun dato.")
