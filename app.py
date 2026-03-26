"""Airbnb Pricing Benchmark — Ca'Mugo & Ca'Mirto vs Competitors"""

import calendar as cal_mod
import json
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from supabase import create_client

from scraper import (
    extract_listing_id,
    fetch_calendar,
    build_stay_windows,
    fetch_prices_for_windows,
    interpolate_daily_prices,
)

# ── Config ─────────────────────────────────────────────────

BENCHMARKS = {
    "Ca'Mugo": {
        "listing_id": "1363939812329907610",
        "icon": "🏔️",
        "accent": "#6366f1",
        "accent_light": "#818cf8",
        "gradient": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
        "location": "Borca di Cadore, Dolomiti",
    },
    "Ca'Mirto": {
        "listing_id": "12323106",
        "icon": "🏖️",
        "accent": "#10b981",
        "accent_light": "#34d399",
        "gradient": "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
        "location": "San Teodoro, Sardegna",
    },
}

COMP_COLOR = "#f43f5e"
COMP_LIGHT = "#fb7185"

SAVED_FILE = Path(__file__).parent / "saved_competitors.json"
REFRESH_FILE = Path(__file__).parent / "last_refresh.json"

# ── Supabase client ───────────────────────────────────────

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

_supabase = None
def _get_db():
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# ── Page config ────────────────────────────────────────────

st.set_page_config(
    page_title="Airbnb Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

# ── Auth gate ─────────────────────────────────────────────

def _check_password() -> bool:
    """Simple password gate using st.secrets or env fallback."""
    import os
    correct_pw = st.secrets.get("password", os.environ.get("APP_PASSWORD", ""))
    if not correct_pw:
        return True  # No password configured → open access

    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <style>
        #MainMenu, footer, header, [data-testid="stSidebarCollapsedControl"],
        [data-testid="stDeployButton"], [data-testid="stToolbar"] {display:none !important;}
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
        html, body, [class*="css"] {font-family:'Inter',sans-serif;}
        .stApp {background:#0f172a;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:70vh;">
        <div style="text-align:center;">
            <div style="font-size:48px;font-weight:900;color:#fff;letter-spacing:-0.04em;margin-bottom:4px;">
                Airbnb <span style="background:linear-gradient(90deg,#a5b4fc,#c4b5fd);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">Benchmark</span>
            </div>
            <div style="font-size:14px;color:rgba(255,255,255,0.35);margin-bottom:40px;">
                Inserisci la password per accedere
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pw = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
        if st.button("Accedi", type="primary", use_container_width=True):
            if pw == correct_pw:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Password errata.")
    return False


if not _check_password():
    st.stop()

# ── Premium CSS — Dark hero + Glass + Animations ──────────

st.markdown("""
<style>
    /* ── Reset ── */
    #MainMenu, footer, header, [data-testid="stSidebarCollapsedControl"],
    [data-testid="stDeployButton"], [data-testid="stToolbar"] {display:none !important;}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] {font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;}
    html {scroll-behavior:smooth;}
    .stApp {background:#f8f9fb;}

    .block-container {max-width:1100px; padding:0 2rem 6rem;}

    /* ── Fade-in animation ── */
    @keyframes fadeInUp {
        from {opacity:0; transform:translateY(20px);}
        to {opacity:1; transform:translateY(0);}
    }
    @keyframes shimmer {
        0% {background-position:200% 0;}
        100% {background-position:-200% 0;}
    }
    @keyframes gradientShift {
        0%,100% {background-position:0% 50%;}
        50% {background-position:100% 50%;}
    }
    .fade-in {animation:fadeInUp 0.6s cubic-bezier(0.16,1,0.3,1) both;}
    .fade-in-d1 {animation-delay:0.1s;}
    .fade-in-d2 {animation-delay:0.2s;}
    .fade-in-d3 {animation-delay:0.3s;}
    .fade-in-d4 {animation-delay:0.4s;}

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background:#fff;
        border:1px solid #eef0f4;
        border-radius:20px;
        padding:28px 28px 24px;
        box-shadow:0 1px 2px rgba(0,0,0,0.02), 0 4px 16px rgba(0,0,0,0.02);
        transition:all 0.3s cubic-bezier(0.16,1,0.3,1);
    }
    [data-testid="stMetric"]:hover {
        box-shadow:0 4px 20px rgba(0,0,0,0.06);
        transform:translateY(-3px);
    }
    [data-testid="stMetric"] label {
        font-size:10px !important; font-weight:700 !important; color:#9ca3af !important;
        text-transform:uppercase; letter-spacing:0.14em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size:32px !important; font-weight:900 !important; color:#111827 !important;
        letter-spacing:-0.04em;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {font-size:13px !important; font-weight:700 !important;}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap:4px; border-bottom:none; background:#f1f3f5; padding:4px;
        border-radius:14px; width:fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight:600; font-size:13px; color:#6b7280;
        padding:8px 20px; border-bottom:none; border-radius:10px;
        transition:all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color:#111827 !important; background:#fff !important;
        box-shadow:0 1px 3px rgba(0,0,0,0.08) !important;
        border-bottom-color:transparent !important;
    }

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {
        background:linear-gradient(135deg, #111827 0%, #1f2937 100%);
        color:#fff; border:none; border-radius:14px;
        padding:14px 40px; font-weight:700; font-size:14px;
        letter-spacing:0.01em;
        box-shadow:0 4px 14px rgba(17,24,39,0.25);
        transition:all 0.25s cubic-bezier(0.16,1,0.3,1);
    }
    .stButton > button[kind="primary"]:hover {
        transform:translateY(-2px);
        box-shadow:0 8px 28px rgba(17,24,39,0.3);
    }
    .stButton > button[kind="secondary"] {
        border-radius:12px; border:1.5px solid #e5e7eb !important;
        font-weight:600; font-size:13px; transition:all 0.2s;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color:#d1d5db !important; background:#f9fafb !important;
        transform:translateY(-1px);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius:14px !important; border:1.5px solid #e5e7eb !important;
        font-size:14px !important; transition:all 0.25s; background:#fff !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:#6366f1 !important;
        box-shadow:0 0 0 4px rgba(99,102,241,0.06) !important;
    }

    /* ── Slider ── */
    .stSlider > div > div > div > div {background:linear-gradient(90deg,#6366f1,#8b5cf6) !important; height:4px !important;}
    .stSlider [data-baseweb="thumb"] {
        background:#fff !important; border:2.5px solid #6366f1 !important;
        box-shadow:0 2px 8px rgba(99,102,241,0.25); width:18px !important; height:18px !important;
    }

    /* ── Divider ── */
    hr {border:none; height:1px; background:linear-gradient(90deg, transparent, #e5e7eb, transparent); margin:48px 0;}

    /* ── Hero section ── */
    .hero {
        background:linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #312e81 70%, #4338ca 100%);
        background-size:300% 300%;
        animation:gradientShift 8s ease infinite;
        border-radius:28px;
        padding:56px 60px 48px;
        margin:0 0 48px;
        position:relative;
        overflow:hidden;
    }
    .hero::before {
        content:'';
        position:absolute; inset:0;
        background:url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        pointer-events:none;
    }
    .hero::after {
        content:'';
        position:absolute;
        bottom:-60%; right:-20%;
        width:500px; height:500px;
        background:radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%);
        pointer-events:none;
    }
    .hero h1 {
        margin:0 0 10px; font-size:48px; font-weight:900; color:#fff;
        letter-spacing:-0.045em; line-height:1.05; position:relative;
    }
    .hero h1 span {
        background:linear-gradient(90deg, #a5b4fc, #c4b5fd, #a5b4fc);
        background-size:200% auto;
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-clip:text;
        animation:shimmer 3s linear infinite;
    }
    .hero p {
        margin:0; font-size:16px; color:rgba(255,255,255,0.55); font-weight:400;
        letter-spacing:-0.01em; position:relative; max-width:480px;
    }
    .hero-badge {
        display:inline-flex; align-items:center; gap:7px;
        padding:7px 16px; border-radius:100px;
        background:rgba(255,255,255,0.06);
        border:1px solid rgba(255,255,255,0.08);
        font-size:12px; font-weight:600; color:rgba(255,255,255,0.5);
        letter-spacing:0.03em; margin-top:20px; position:relative;
        backdrop-filter:blur(8px);
    }
    .hero-badge .dot {width:6px;height:6px;border-radius:50%;background:#34d399;animation:pulse 2s infinite;}
    @keyframes pulse {
        0%,100% {opacity:1; box-shadow:0 0 0 0 rgba(52,211,153,0.4);}
        50% {opacity:0.6; box-shadow:0 0 0 6px rgba(52,211,153,0);}
    }

    /* ── Section headers ── */
    .section-title {
        font-size:18px; font-weight:800; color:#111827; letter-spacing:-0.03em;
        margin:48px 0 24px; display:flex; align-items:center; gap:12px;
    }
    .section-title .icon {font-size:14px; opacity:0.5;}
    .section-title .line {flex:1; height:1px; background:linear-gradient(90deg, #e5e7eb, transparent);}

    /* ── Calendar ── */
    .cal-wrap {
        background:#fff; border-radius:24px; padding:36px;
        border:1px solid #eef0f4;
        box-shadow:0 1px 2px rgba(0,0,0,0.02), 0 4px 16px rgba(0,0,0,0.02);
        margin-bottom:28px;
    }
    .cal-month-title {
        font-size:24px; font-weight:900; color:#111827;
        letter-spacing:-0.04em; margin-bottom:24px;
    }
    .cal-month-title span {font-weight:400; color:#9ca3af;}
    .cal-table {border-collapse:separate; border-spacing:4px; width:100%; text-align:center; font-family:Inter,sans-serif;}
    .cal-table th {
        padding:12px 4px; font-size:9px; font-weight:800; color:#9ca3af;
        text-transform:uppercase; letter-spacing:0.16em;
    }
    .cal-table td {
        padding:10px 6px; border-radius:16px; vertical-align:top; min-width:100px;
        background:#f9fafb; border:1.5px solid #f3f4f6;
        transition:all 0.25s cubic-bezier(0.16,1,0.3,1);
    }
    .cal-table td:hover {
        background:#fff; border-color:#e5e7eb;
        box-shadow:0 4px 16px rgba(0,0,0,0.05);
        transform:translateY(-2px);
    }
    .cal-day-num {font-weight:900; font-size:16px; color:#374151; margin-bottom:6px; letter-spacing:-0.02em;}
    .cal-past {color:#d1d5db !important; font-weight:400;}
    .cal-bench {font-weight:800; font-size:12px; letter-spacing:-0.01em;}
    .cal-comp {font-weight:800; font-size:12px; letter-spacing:-0.01em;}
    .cal-min {font-size:8px; font-weight:700; opacity:0.45; margin-left:2px;}
    .cal-booked {
        font-size:7px; font-weight:800; letter-spacing:0.1em;
        text-transform:uppercase; padding:2px 7px; border-radius:5px;
        display:inline-block; margin-top:2px;
    }
    .cal-cheaper-bench {background:#ecfdf5 !important; border-color:#a7f3d0 !important;}
    .cal-cheaper-comp {background:#fff1f2 !important; border-color:#fecdd3 !important;}
    .cal-same {background:#f9fafb !important; border-color:#f3f4f6 !important;}
    .cal-today {border-color:#6366f1 !important; border-width:2.5px !important; box-shadow:0 0 0 3px rgba(99,102,241,0.08);}

    /* ── Legend bar ── */
    .legend-bar {
        display:flex; flex-wrap:wrap; gap:20px; align-items:center;
        padding:16px 24px; border-radius:16px;
        background:#fff; border:1px solid #eef0f4;
        font-size:12px; font-weight:600; color:#6b7280;
        margin-bottom:28px;
        box-shadow:0 1px 2px rgba(0,0,0,0.02);
    }
    .legend-dot {width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px;}
    .legend-tag {
        padding:4px 12px; border-radius:8px; font-size:11px; font-weight:700;
        letter-spacing:0.02em;
    }

    /* ── Dataframe ── */
    .stDataFrame {border-radius:16px !important; overflow:hidden;}
    .stDataFrame [data-testid="stDataFrameResizable"] {border-radius:16px; border:1px solid #eef0f4;}

    /* ── Progress bar ── */
    .stProgress > div > div > div {
        background:linear-gradient(90deg,#6366f1,#8b5cf6) !important;
        border-radius:100px;
    }

    /* ── Property selector card ── */
    .prop-card {
        background:#fff; border:1px solid #eef0f4; border-radius:20px;
        padding:24px 28px; margin-bottom:8px;
        box-shadow:0 1px 2px rgba(0,0,0,0.02);
    }

    /* ── Footer ── */
    .app-footer {
        text-align:center; padding:64px 0 0;
        font-size:11px; font-weight:500; color:#d1d5db;
        letter-spacing:0.04em; text-transform:uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ── Saved competitors (per-property) ──────────────────────

def _load_saved(property_name: str) -> list[dict]:
    db = _get_db()
    if db:
        resp = db.table("saved_competitors").select("*").eq("property_name", property_name).execute()
        return [{"name": r["competitor_name"], "url": r["airbnb_url"], "listing_id": r["listing_id"]} for r in resp.data]
    # Fallback to file
    if SAVED_FILE.exists():
        data = json.loads(SAVED_FILE.read_text())
        if isinstance(data, list):
            data = {"Ca'Mugo": data}
        return data.get(property_name, [])
    return []


def _add_competitor(property_name: str, name: str, url: str):
    listing_id = extract_listing_id(url)
    db = _get_db()
    if db:
        db.table("saved_competitors").upsert({
            "property_name": property_name,
            "competitor_name": name,
            "airbnb_url": url,
            "listing_id": listing_id,
        }, on_conflict="property_name,listing_id").execute()
    else:
        # Fallback to file
        if SAVED_FILE.exists():
            all_comps = json.loads(SAVED_FILE.read_text())
            if isinstance(all_comps, list):
                all_comps = {"Ca'Mugo": all_comps}
        else:
            all_comps = {}
        comps = all_comps.get(property_name, [])
        if not any(c["listing_id"] == listing_id for c in comps):
            comps.append({"name": name, "url": url, "listing_id": listing_id})
            all_comps[property_name] = comps
            SAVED_FILE.write_text(json.dumps(all_comps, indent=2))


def _remove_competitor(property_name: str, listing_id: str):
    db = _get_db()
    if db:
        db.table("saved_competitors").delete().eq("property_name", property_name).eq("listing_id", listing_id).execute()
    else:
        if SAVED_FILE.exists():
            all_comps = json.loads(SAVED_FILE.read_text())
            if isinstance(all_comps, list):
                all_comps = {"Ca'Mugo": all_comps}
            comps = all_comps.get(property_name, [])
            all_comps[property_name] = [c for c in comps if c["listing_id"] != listing_id]
            SAVED_FILE.write_text(json.dumps(all_comps, indent=2))


# ── Fetch helper ──────────────────────────────────────────


def _fetch_property(listing_id: str, n_calls: int, months: int = 4) -> dict:
    today = date.today()
    cal_days = fetch_calendar(listing_id, today.month, today.year, count=months)
    if not cal_days:
        return {"days": [], "windows": []}
    windows = build_stay_windows(cal_days)
    priced = fetch_prices_for_windows(listing_id, windows, max_calls=n_calls)
    enriched = interpolate_daily_prices(cal_days, priced)
    return {"days": enriched, "windows": priced}


# ── Hero ──────────────────────────────────────────────────

st.markdown("""
<div class="hero fade-in">
    <h1>Airbnb<br><span>Benchmark</span></h1>
    <p>Confronta prezzi e disponibilità delle tue property con i competitor — dati aggiornati in tempo reale.</p>
    <div class="hero-badge">
        <span class="dot"></span>
        Live via Airbnb API
    </div>
</div>
""", unsafe_allow_html=True)

# ── Property selector ──────────────────────────────────────

col_prop, col_spacer = st.columns([2, 3])
with col_prop:
    bench_name = st.selectbox(
        "La tua property",
        list(BENCHMARKS.keys()),
        format_func=lambda x: f"{BENCHMARKS[x]['icon']}  {x}  ·  {BENCHMARKS[x]['location']}",
    )

bench = BENCHMARKS[bench_name]

# ── Refresh benchmark data ────────────────────────────────

def _load_refresh_time(prop_name: str) -> str | None:
    db = _get_db()
    if db:
        resp = db.table("refresh_log").select("last_refresh").eq("property_name", prop_name).execute()
        if resp.data:
            ts = resp.data[0]["last_refresh"]
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return ts
    # Fallback to file
    if REFRESH_FILE.exists():
        return json.loads(REFRESH_FILE.read_text()).get(prop_name)
    return None

def _save_refresh_time(prop_name: str):
    db = _get_db()
    if db:
        db.table("refresh_log").upsert({
            "property_name": prop_name,
            "last_refresh": datetime.utcnow().isoformat(),
        }, on_conflict="property_name").execute()
    else:
        data = {}
        if REFRESH_FILE.exists():
            data = json.loads(REFRESH_FILE.read_text())
        data[prop_name] = datetime.now().strftime("%d/%m/%Y %H:%M")
        REFRESH_FILE.write_text(json.dumps(data))

last_refresh = _load_refresh_time(bench_name)

col_refresh, col_ts = st.columns([1, 4])
with col_refresh:
    refresh_bench = st.button("🔄 Aggiorna dati property", use_container_width=True)
with col_ts:
    if last_refresh:
        st.markdown(
            f'<div style="padding:10px 0;font-size:13px;color:#94a3b8;">'
            f'Ultimo aggiornamento: <strong style="color:#64748b;">{last_refresh}</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="padding:10px 0;font-size:13px;color:#94a3b8;">Mai aggiornato</div>',
            unsafe_allow_html=True,
        )

if refresh_bench:
    months = st.session_state.get("_months_ahead", 4)
    n_calls = 10
    with st.spinner(f"Aggiornamento {bench_name}..."):
        bench_data = _fetch_property(bench["listing_id"], n_calls, months)
        st.session_state["bench"] = bench_data
        st.session_state["bench_name"] = bench_name
    # Also refresh competitor if one was loaded before
    comp_id = st.session_state.get("comp_id")
    if comp_id:
        with st.spinner("Aggiornamento competitor..."):
            comp_data = _fetch_property(comp_id, n_calls, months)
            st.session_state["comp"] = comp_data
    _save_refresh_time(bench_name)
    st.rerun()

st.divider()

# ── Competitor selection ───────────────────────────────────

saved = _load_saved(bench_name)

tab_saved, tab_new, tab_manage = st.tabs(["Salvati", "Nuovo URL", "Gestisci"])

with tab_saved:
    if saved:
        options = {f"{c['name']}  ·  {c['listing_id']}": c for c in saved}
        selected_label = st.selectbox(
            "Scegli competitor",
            list(options.keys()),
            label_visibility="collapsed",
        )
        selected_comp = options[selected_label]
        comp_url_to_use = selected_comp["url"]
    else:
        st.markdown(
            '<p style="color:#94a3b8;font-size:14px;padding:20px 0;">'
            'Nessun competitor salvato. Aggiungi un URL nella tab <strong>Nuovo URL</strong>.</p>',
            unsafe_allow_html=True,
        )
        comp_url_to_use = None

with tab_new:
    new_url = st.text_input(
        "URL Airbnb",
        placeholder="https://www.airbnb.com/rooms/12345678",
        key="new_comp_url",
        label_visibility="collapsed",
    )
    col_name, col_save = st.columns([4, 1])
    with col_name:
        new_name = st.text_input("Nome", placeholder="Es: Chalet Cortina", key="new_comp_name", label_visibility="collapsed")
    with col_save:
        if st.button("Salva", use_container_width=True):
            if new_url:
                try:
                    lid = extract_listing_id(new_url)
                    label = new_name or f"Listing {lid}"
                    _add_competitor(bench_name, label, new_url)
                    st.success(f"Salvato: {label}")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
    if new_url:
        comp_url_to_use = new_url

with tab_manage:
    if saved:
        for c in saved:
            col_info, col_del = st.columns([6, 1])
            with col_info:
                st.markdown(
                    f'<div style="padding:10px 0;font-size:14px;">'
                    f'<strong style="color:#0f172a;">{c["name"]}</strong>'
                    f'<span style="color:#94a3b8;margin-left:8px;font-size:12px;">ID {c["listing_id"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("Rimuovi", key=f"del_{c['listing_id']}", type="secondary"):
                    _remove_competitor(bench_name, c["listing_id"])
                    st.rerun()
    else:
        st.markdown('<p style="color:#94a3b8;font-size:14px;padding:20px 0;">Lista vuota.</p>', unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Launch analysis ────────────────────────────────────────

col_months, col_slider, col_btn = st.columns([2, 3, 1])
with col_months:
    months_ahead = st.select_slider(
        "Mesi in avanti",
        options=list(range(1, 13)),
        value=4,
        key="_months_ahead",
        help="Quanti mesi di calendario analizzare (1-12)",
    )
with col_slider:
    max_price_calls = st.slider(
        "Precisione prezzo",
        5, 30, 10,
        help="Numero di chiamate API per property. Di più = prezzi più precisi, più lento.",
    )
with col_btn:
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    go = st.button("Confronta", type="primary", use_container_width=True)

if go:
    if not comp_url_to_use:
        st.warning("Seleziona o inserisci un competitor.")
        st.stop()

    try:
        comp_id = extract_listing_id(comp_url_to_use)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    progress = st.progress(0, text=f"Scaricamento {bench_name}...")
    bench_data = _fetch_property(bench["listing_id"], max_price_calls, months_ahead)
    progress.progress(50, text="Scaricamento competitor...")
    comp_data = _fetch_property(comp_id, max_price_calls, months_ahead)
    progress.progress(100, text="Completato")

    st.session_state["bench"] = bench_data
    st.session_state["comp"] = comp_data
    st.session_state["comp_id"] = comp_id
    st.session_state["bench_name"] = bench_name

# ── Display results ────────────────────────────────────────

if "bench" not in st.session_state or "comp" not in st.session_state:
    st.stop()

bench_data = st.session_state["bench"]
comp_data = st.session_state["comp"]
active_bench = st.session_state.get("bench_name", bench_name)
active = BENCHMARKS.get(active_bench, bench)
ac = active["accent"]

bench_days = {d["date"]: d for d in bench_data["days"]}
comp_days = {d["date"]: d for d in comp_data["days"]}
all_dates = sorted(set(list(bench_days.keys()) + list(comp_days.keys())))

st.divider()

# ── Summary metrics ────────────────────────────────────────

st.markdown(f'<div class="section-title fade-in">Riepilogo<span class="line"></span></div>', unsafe_allow_html=True)

bench_prices = [d["nightly_price"] for d in bench_data["days"] if d.get("nightly_price")]
comp_prices = [d["nightly_price"] for d in comp_data["days"] if d.get("nightly_price")]
bench_avg = sum(bench_prices) / len(bench_prices) if bench_prices else 0
comp_avg = sum(comp_prices) / len(comp_prices) if comp_prices else 0
bench_avail = sum(1 for d in bench_data["days"] if d["available"])
comp_avail = sum(1 for d in comp_data["days"] if d["available"])

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{active_bench} media/notte", f"€{bench_avg:.0f}" if bench_prices else "N/D")
c2.metric("Competitor media/notte", f"€{comp_avg:.0f}" if comp_prices else "N/D")
if bench_prices and comp_prices:
    diff = bench_avg - comp_avg
    pct = (diff / comp_avg) * 100 if comp_avg else 0
    c3.metric("Delta prezzo", f"{pct:+.0f}%", delta=f"€{diff:+.0f}")
else:
    c3.metric("Delta prezzo", "N/D")
c4.metric("Giorni disponibili", f"{bench_avail} vs {comp_avail}")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Legend ──────────────────────────────────────────────────

st.markdown(f"""
<div class="legend-bar fade-in fade-in-d1">
    <span><span class="legend-dot" style="background:{ac};"></span> {active_bench}</span>
    <span><span class="legend-dot" style="background:{COMP_COLOR};"></span> Competitor</span>
    <span style="color:#94a3b8;">|</span>
    <span class="legend-tag" style="background:#ecfdf5;color:#065f46;">{active_bench} meno caro</span>
    <span class="legend-tag" style="background:#fff1f2;color:#9f1239;">Competitor meno caro</span>
    <span style="color:#94a3b8;">|</span>
    <span style="font-weight:700;color:#475569;">BOOKED</span> = occupato
</div>
""", unsafe_allow_html=True)

# ── Calendar ───────────────────────────────────────────────

st.markdown(f'<div class="section-title fade-in fade-in-d2">Calendario prezzi<span class="line"></span></div>', unsafe_allow_html=True)

months_set: dict[tuple, list] = defaultdict(list)
for dt_str in all_dates:
    dt = date.fromisoformat(dt_str)
    months_set[(dt.year, dt.month)].append(dt_str)

today = date.today()

for (year, month), _ in sorted(months_set.items()):
    month_name = cal_mod.month_name[month]

    html = f'<div class="cal-wrap fade-in">'
    html += f'<div class="cal-month-title">{month_name} <span>{year}</span></div>'

    weeks = cal_mod.monthcalendar(year, month)

    html += '<table class="cal-table">'
    html += "<tr>"
    for hdr in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
        html += f"<th>{hdr}</th>"
    html += "</tr>"

    for week in weeks:
        html += "<tr>"
        for day_num in week:
            if day_num == 0:
                html += '<td style="border:none;background:none;"></td>'
                continue

            dt = date(year, month, day_num)
            dt_str = dt.isoformat()
            b = bench_days.get(dt_str)
            c = comp_days.get(dt_str)

            is_today = dt == today
            today_cls = " cal-today" if is_today else ""

            if dt < today:
                html += f'<td style="border:none;background:none;"><span class="cal-day-num cal-past">{day_num}</span></td>'
                continue

            # Benchmark line
            if b and not b["available"]:
                b_html = f'<div class="cal-booked" style="color:{ac};background:{ac}12;">booked</div>'
            elif b and b.get("nightly_price"):
                b_html = (
                    f'<div><span class="cal-bench" style="color:{ac};">€{b["nightly_price"]:.0f}</span>'
                    f'<span class="cal-min" style="color:{ac};"> {b["minNights"]}n</span></div>'
                )
            elif b:
                b_html = '<div style="color:#cbd5e1;font-size:10px;">—</div>'
            else:
                b_html = ""

            # Competitor line
            if c and not c["available"]:
                c_html = f'<div class="cal-booked" style="color:{COMP_COLOR};background:{COMP_COLOR}12;">booked</div>'
            elif c and c.get("nightly_price"):
                c_html = (
                    f'<div><span class="cal-comp" style="color:{COMP_COLOR};">€{c["nightly_price"]:.0f}</span>'
                    f'<span class="cal-min" style="color:{COMP_COLOR};"> {c["minNights"]}n</span></div>'
                )
            elif c:
                c_html = '<div style="color:#cbd5e1;font-size:10px;">—</div>'
            else:
                c_html = ""

            # Cell class for color coding
            cell_class = ""
            if b and b.get("nightly_price") and c and c.get("nightly_price"):
                bp, cp = b["nightly_price"], c["nightly_price"]
                if bp < cp:
                    cell_class = "cal-cheaper-bench"
                elif bp > cp:
                    cell_class = "cal-cheaper-comp"
                else:
                    cell_class = "cal-same"

            html += (
                f'<td class="{cell_class}{today_cls}">'
                f'<div class="cal-day-num">{day_num}</div>'
                f'{b_html}{c_html}'
                f'</td>'
            )
        html += "</tr>"
    html += "</table>"
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

# ── Price windows detail ───────────────────────────────────

st.markdown(f'<div class="section-title fade-in fade-in-d3">Dettaglio finestre di prezzo<span class="line"></span></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{ac};"></span>'
        f'<span style="font-size:13px;font-weight:800;color:{ac};text-transform:uppercase;'
        f'letter-spacing:0.06em;">{active_bench}</span></div>',
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
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.caption("Nessun dato.")

with col2:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{COMP_COLOR};"></span>'
        f'<span style="font-size:13px;font-weight:800;color:{COMP_COLOR};text-transform:uppercase;'
        f'letter-spacing:0.06em;">Competitor</span></div>',
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
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.caption("Nessun dato.")

# ── Footer ─────────────────────────────────────────────────

st.markdown("""
<div class="app-footer">
    Airbnb Benchmark &nbsp;·&nbsp; Dati via Airbnb Internal API &nbsp;·&nbsp; Prezzi in EUR
</div>
""", unsafe_allow_html=True)
