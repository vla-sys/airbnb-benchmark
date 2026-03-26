"""Airbnb Pricing Benchmark — Ca'Mugo & Ca'Mirto vs Competitors"""

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

BENCHMARKS = {
    "Ca'Mugo": {
        "listing_id": "1363939812329907610",
        "icon": "🏔️",
        "color": "#2563eb",
        "location": "Borca di Cadore, Dolomiti",
    },
    "Ca'Mirto": {
        "listing_id": "12323106",
        "icon": "🏖️",
        "color": "#059669",
        "location": "San Teodoro, Sardegna",
    },
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

# ── Premium CSS ────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Reset & Base ── */
    #MainMenu, footer, header, [data-testid="stSidebarCollapsedControl"] {display:none !important;}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;}
    html {scroll-behavior:smooth;}

    /* ── Container max-width for breathing room ── */
    .block-container {max-width:1100px; padding:2rem 2rem 4rem;}

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background:#fff;
        border:1px solid #e5e7eb;
        border-radius:16px;
        padding:20px 24px;
        box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 4px 12px rgba(0,0,0,0.02);
        transition:box-shadow 0.2s, transform 0.2s;
    }
    [data-testid="stMetric"]:hover {
        box-shadow:0 2px 4px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.04);
        transform:translateY(-1px);
    }
    [data-testid="stMetric"] label {
        font-size:11px !important; font-weight:600 !important; color:#9ca3af !important;
        text-transform:uppercase; letter-spacing:0.08em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size:32px !important; font-weight:800 !important; color:#111827 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {font-size:13px !important;}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {gap:0; border-bottom:2px solid #f3f4f6;}
    .stTabs [data-baseweb="tab"] {
        font-weight:500; font-size:14px; color:#6b7280;
        padding:12px 24px; border-bottom:2px solid transparent;
        margin-bottom:-2px; transition:all 0.15s;
    }
    .stTabs [aria-selected="true"] {
        color:#111827 !important; border-bottom-color:#111827 !important; font-weight:600;
    }

    /* ── Primary button ── */
    .stButton > button[kind="primary"] {
        background:#111827; color:#fff; border:none; border-radius:12px;
        padding:14px 32px; font-weight:600; font-size:15px;
        letter-spacing:-0.01em; box-shadow:0 1px 3px rgba(0,0,0,0.1), 0 4px 12px rgba(0,0,0,0.08);
        transition:all 0.15s;
    }
    .stButton > button[kind="primary"]:hover {
        background:#1f2937; box-shadow:0 2px 6px rgba(0,0,0,0.12), 0 8px 24px rgba(0,0,0,0.1);
        transform:translateY(-1px);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius:12px !important; border:1.5px solid #e5e7eb !important;
        font-size:14px !important; transition:border-color 0.15s;
    }
    .stTextInput > div > div > input:focus {
        border-color:#111827 !important; box-shadow:0 0 0 3px rgba(17,24,39,0.06) !important;
    }

    /* ── Slider ── */
    .stSlider > div > div > div > div {background:#111827 !important;}
    .stSlider [data-baseweb="thumb"] {background:#111827 !important; border:3px solid #fff !important; box-shadow:0 1px 4px rgba(0,0,0,0.15);}

    /* ── Divider ── */
    hr {border:none; height:1px; background:#f3f4f6; margin:32px 0;}

    /* ── Custom classes ── */
    .header-badge {
        display:inline-flex; align-items:center; gap:6px;
        padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600;
        letter-spacing:0.02em;
    }
    .month-header {
        font-size:18px; font-weight:700; color:#111827; letter-spacing:-0.02em;
        margin:32px 0 16px; padding-bottom:8px; border-bottom:2px solid #f3f4f6;
    }

    /* ── Calendar table ── */
    .cal-table {border-collapse:separate; border-spacing:4px; width:100%; text-align:center; font-family:Inter,sans-serif;}
    .cal-table th {padding:8px 4px; font-size:10px; font-weight:700; color:#9ca3af; text-transform:uppercase; letter-spacing:0.1em;}
    .cal-table td {
        padding:8px 4px; border-radius:10px; vertical-align:top; min-width:90px;
        border:1px solid #f3f4f6; background:#fff; transition:background 0.15s;
    }
    .cal-table td:hover {background:#fafafa;}
    .cal-day-num {font-weight:700; font-size:14px; color:#374151; margin-bottom:4px;}
    .cal-past {color:#d1d5db !important; font-weight:400;}
    .cal-bench {font-weight:700; font-size:11px;}
    .cal-comp {font-weight:700; font-size:11px; color:#dc2626;}
    .cal-min {font-size:9px; font-weight:500; opacity:0.6;}
    .cal-booked {font-size:9px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase;}
    .cal-cheaper-bench {background:#f0fdf4 !important; border-color:#bbf7d0 !important;}
    .cal-cheaper-comp {background:#fef2f2 !important; border-color:#fecaca !important;}
    .cal-same {background:#fafafa !important; border-color:#e5e7eb !important;}
</style>
""", unsafe_allow_html=True)


# ── Saved competitors (per-property) ──────────────────────

def _load_all_saved() -> dict[str, list[dict]]:
    """Load saved competitors dict keyed by property name."""
    if SAVED_FILE.exists():
        data = json.loads(SAVED_FILE.read_text())
        # Migrate from old flat list format
        if isinstance(data, list):
            return {"Ca'Mugo": data}
        return data
    return {}


def _load_saved(property_name: str) -> list[dict]:
    return _load_all_saved().get(property_name, [])


def _save_all(all_comps: dict[str, list[dict]]):
    SAVED_FILE.write_text(json.dumps(all_comps, indent=2))


def _add_competitor(property_name: str, name: str, url: str):
    all_comps = _load_all_saved()
    comps = all_comps.get(property_name, [])
    listing_id = extract_listing_id(url)
    if not any(c["listing_id"] == listing_id for c in comps):
        comps.append({"name": name, "url": url, "listing_id": listing_id})
        all_comps[property_name] = comps
        _save_all(all_comps)


def _remove_competitor(property_name: str, listing_id: str):
    all_comps = _load_all_saved()
    comps = all_comps.get(property_name, [])
    all_comps[property_name] = [c for c in comps if c["listing_id"] != listing_id]
    _save_all(all_comps)


# ── Header ─────────────────────────────────────────────────

st.markdown("""
<div style="margin-bottom:32px;">
    <h1 style="margin:0 0 4px;font-size:36px;font-weight:800;color:#111827;letter-spacing:-0.03em;">
        Airbnb Benchmark</h1>
    <p style="margin:0;font-size:15px;color:#6b7280;font-weight:400;">
        Confronta i prezzi delle tue property con i competitor — calendario 120 giorni</p>
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
            '<p style="color:#9ca3af;font-size:14px;padding:16px 0;">'
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
                    f'<div style="padding:8px 0;font-size:14px;">'
                    f'<strong>{c["name"]}</strong>'
                    f'<span style="color:#9ca3af;margin-left:8px;">ID {c["listing_id"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("Rimuovi", key=f"del_{c['listing_id']}", type="secondary"):
                    _remove_competitor(bench_name, c["listing_id"])
                    st.rerun()
    else:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0;">Lista vuota.</p>', unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Launch analysis ────────────────────────────────────────

col_slider, col_btn = st.columns([4, 1])
with col_slider:
    max_price_calls = st.slider(
        "Precisione prezzo",
        5, 30, 10,
        help="Più chiamate API = prezzi più precisi, ma più lento",
    )
with col_btn:
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    go = st.button("Confronta", type="primary", use_container_width=True)

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

    progress = st.progress(0, text=f"Scaricamento {bench_name}...")
    bench_data = _fetch_property(bench["listing_id"], max_price_calls)
    progress.progress(50, text="Scaricamento competitor...")
    comp_data = _fetch_property(comp_id, max_price_calls)
    progress.progress(100, text="Completato")

    st.session_state["bench"] = bench_data
    st.session_state["comp"] = comp_data
    st.session_state["comp_id"] = comp_id
    st.session_state["bench_name"] = bench_name

# ── Display results ────────────────────────────────────────

if "bench" not in st.session_state:
    st.stop()

bench_data = st.session_state["bench"]
comp_data = st.session_state["comp"]
active_bench = st.session_state.get("bench_name", bench_name)
active_color = BENCHMARKS.get(active_bench, bench)["color"]

bench_days = {d["date"]: d for d in bench_data["days"]}
comp_days = {d["date"]: d for d in comp_data["days"]}
all_dates = sorted(set(list(bench_days.keys()) + list(comp_days.keys())))

st.divider()

# ── Summary metrics ────────────────────────────────────────

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

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Legend ──────────────────────────────────────────────────

st.markdown(f"""
<div style="display:flex;gap:20px;align-items:center;padding:10px 16px;
            background:#fafafa;border-radius:12px;font-size:12px;font-weight:500;color:#6b7280;">
    <span style="display:flex;align-items:center;gap:4px;">
        <span style="width:8px;height:8px;border-radius:50%;background:{active_color};"></span>
        {active_bench}</span>
    <span style="display:flex;align-items:center;gap:4px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#dc2626;"></span>
        Competitor</span>
    <span>Occupato = <span style="font-weight:700;">BOOKED</span></span>
    <span style="background:#f0fdf4;padding:2px 10px;border-radius:6px;color:#166534;">{active_bench} meno caro</span>
    <span style="background:#fef2f2;padding:2px 10px;border-radius:6px;color:#991b1b;">Competitor meno caro</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Calendar ───────────────────────────────────────────────

months_set: dict[tuple, list] = defaultdict(list)
for dt_str in all_dates:
    dt = date.fromisoformat(dt_str)
    months_set[(dt.year, dt.month)].append(dt_str)

today = date.today()

for (year, month), _ in sorted(months_set.items()):
    month_name = cal_mod.month_name[month]
    st.markdown(f'<div class="month-header">{month_name} {year}</div>', unsafe_allow_html=True)

    weeks = cal_mod.monthcalendar(year, month)

    html = '<table class="cal-table">'
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

            if dt < today:
                html += f'<td style="border:none;background:none;"><span class="cal-day-num cal-past">{day_num}</span></td>'
                continue

            # Benchmark line
            if b and not b["available"]:
                b_html = f'<div class="cal-booked" style="color:{active_color};">booked</div>'
            elif b and b.get("nightly_price"):
                b_html = (
                    f'<div><span class="cal-bench" style="color:{active_color};">€{b["nightly_price"]:.0f}</span>'
                    f'<span class="cal-min" style="color:{active_color};"> {b["minNights"]}n</span></div>'
                )
            elif b:
                b_html = f'<div style="color:#d1d5db;font-size:10px;">—</div>'
            else:
                b_html = ""

            # Competitor line
            if c and not c["available"]:
                c_html = '<div class="cal-booked" style="color:#dc2626;">booked</div>'
            elif c and c.get("nightly_price"):
                c_html = (
                    f'<div><span class="cal-comp">€{c["nightly_price"]:.0f}</span>'
                    f'<span class="cal-min" style="color:#dc2626;"> {c["minNights"]}n</span></div>'
                )
            elif c:
                c_html = '<div style="color:#d1d5db;font-size:10px;">—</div>'
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
                f'<td class="{cell_class}">'
                f'<div class="cal-day-num">{day_num}</div>'
                f'{b_html}{c_html}'
                f'</td>'
            )
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ── Price windows detail ───────────────────────────────────
st.markdown(
    '<div class="month-header">Dettaglio finestre di prezzo</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<p style="font-size:13px;font-weight:700;color:{active_color};margin-bottom:4px;'
        f'text-transform:uppercase;letter-spacing:0.06em;">{active_bench}</p>',
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
        '<p style="font-size:13px;font-weight:700;color:#dc2626;margin-bottom:4px;'
        'text-transform:uppercase;letter-spacing:0.06em;">Competitor</p>',
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
<div style="text-align:center;padding:32px 0 0;color:#d1d5db;font-size:11px;font-weight:400;">
    Airbnb Benchmark · Dati via Airbnb internal API · Prezzi in EUR
</div>
""", unsafe_allow_html=True)
