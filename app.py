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

# ── Page config ────────────────────────────────────────────

st.set_page_config(
    page_title="Airbnb Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

# ── Premium CSS — Dark hero + Glass + Animations ──────────

st.markdown("""
<style>
    /* ── Reset ── */
    #MainMenu, footer, header, [data-testid="stSidebarCollapsedControl"],
    [data-testid="stDeployButton"] {display:none !important;}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] {font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;}
    html {scroll-behavior:smooth;}

    .block-container {max-width:1200px; padding:0 2rem 4rem;}

    /* ── Fade-in animation ── */
    @keyframes fadeInUp {
        from {opacity:0; transform:translateY(16px);}
        to {opacity:1; transform:translateY(0);}
    }
    .fade-in {animation:fadeInUp 0.5s ease-out both;}
    .fade-in-d1 {animation-delay:0.08s;}
    .fade-in-d2 {animation-delay:0.16s;}
    .fade-in-d3 {animation-delay:0.24s;}
    .fade-in-d4 {animation-delay:0.32s;}

    /* ── Glass card ── */
    .glass {
        background:rgba(255,255,255,0.7);
        backdrop-filter:blur(20px);
        -webkit-backdrop-filter:blur(20px);
        border:1px solid rgba(255,255,255,0.3);
        border-radius:20px;
        box-shadow:0 4px 30px rgba(0,0,0,0.04);
    }

    /* ── Metric cards (Streamlit overrides) ── */
    [data-testid="stMetric"] {
        background:rgba(255,255,255,0.85);
        backdrop-filter:blur(12px);
        border:1px solid rgba(0,0,0,0.04);
        border-radius:20px;
        padding:24px 28px;
        box-shadow:0 1px 3px rgba(0,0,0,0.02), 0 8px 32px rgba(0,0,0,0.03);
        transition:all 0.25s cubic-bezier(0.4,0,0.2,1);
    }
    [data-testid="stMetric"]:hover {
        box-shadow:0 2px 8px rgba(0,0,0,0.04), 0 16px 48px rgba(0,0,0,0.06);
        transform:translateY(-2px);
    }
    [data-testid="stMetric"] label {
        font-size:10px !important; font-weight:700 !important; color:#94a3b8 !important;
        text-transform:uppercase; letter-spacing:0.12em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size:36px !important; font-weight:900 !important; color:#0f172a !important;
        letter-spacing:-0.03em;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {font-size:13px !important; font-weight:600 !important;}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {gap:0; border-bottom:2px solid #f1f5f9; background:transparent;}
    .stTabs [data-baseweb="tab"] {
        font-weight:500; font-size:13px; color:#94a3b8;
        padding:10px 20px; border-bottom:2px solid transparent;
        margin-bottom:-2px; transition:all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color:#0f172a !important; border-bottom-color:#0f172a !important; font-weight:700;
    }

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {
        background:#0f172a; color:#fff; border:none; border-radius:14px;
        padding:14px 36px; font-weight:700; font-size:14px;
        letter-spacing:0.01em;
        box-shadow:0 2px 8px rgba(15,23,42,0.15), 0 8px 32px rgba(15,23,42,0.1);
        transition:all 0.2s cubic-bezier(0.4,0,0.2,1);
    }
    .stButton > button[kind="primary"]:hover {
        background:#1e293b;
        box-shadow:0 4px 12px rgba(15,23,42,0.2), 0 16px 48px rgba(15,23,42,0.15);
        transform:translateY(-2px);
    }
    .stButton > button[kind="secondary"] {
        border-radius:12px; border:1.5px solid #e2e8f0 !important;
        font-weight:600; font-size:13px; transition:all 0.15s;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color:#cbd5e1 !important; background:#f8fafc !important;
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius:14px !important; border:1.5px solid #e2e8f0 !important;
        font-size:14px !important; transition:all 0.2s; background:#fff !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:#6366f1 !important;
        box-shadow:0 0 0 3px rgba(99,102,241,0.08) !important;
    }

    /* ── Slider ── */
    .stSlider > div > div > div > div {background:#0f172a !important;}
    .stSlider [data-baseweb="thumb"] {
        background:#0f172a !important; border:3px solid #fff !important;
        box-shadow:0 2px 8px rgba(0,0,0,0.15);
    }

    /* ── Divider ── */
    hr {border:none; height:1px; background:linear-gradient(90deg, transparent, #e2e8f0, transparent); margin:40px 0;}

    /* ── Hero section ── */
    .hero {
        background:linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        border-radius:28px;
        padding:48px 56px;
        margin:0 0 40px;
        position:relative;
        overflow:hidden;
    }
    .hero::before {
        content:'';
        position:absolute;
        top:-50%; right:-20%;
        width:600px; height:600px;
        background:radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
        pointer-events:none;
    }
    .hero::after {
        content:'';
        position:absolute;
        bottom:-30%; left:-10%;
        width:400px; height:400px;
        background:radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%);
        pointer-events:none;
    }
    .hero h1 {
        margin:0 0 8px; font-size:44px; font-weight:900; color:#fff;
        letter-spacing:-0.04em; line-height:1.1; position:relative;
    }
    .hero p {
        margin:0; font-size:16px; color:#94a3b8; font-weight:400;
        letter-spacing:-0.01em; position:relative;
    }
    .hero-badge {
        display:inline-flex; align-items:center; gap:6px;
        padding:6px 14px; border-radius:100px;
        background:rgba(255,255,255,0.08);
        border:1px solid rgba(255,255,255,0.06);
        font-size:12px; font-weight:600; color:#cbd5e1;
        letter-spacing:0.02em; margin-top:16px; position:relative;
    }
    .hero-badge .dot {width:6px;height:6px;border-radius:50%;background:#10b981;animation:pulse 2s infinite;}
    @keyframes pulse {
        0%,100% {opacity:1;}
        50% {opacity:0.4;}
    }

    /* ── Section headers ── */
    .section-title {
        font-size:20px; font-weight:800; color:#0f172a; letter-spacing:-0.03em;
        margin:40px 0 20px; display:flex; align-items:center; gap:10px;
    }
    .section-title .line {flex:1; height:1px; background:#e2e8f0;}

    /* ── Calendar ── */
    .cal-wrap {
        background:#fff; border-radius:24px; padding:32px;
        border:1px solid #f1f5f9;
        box-shadow:0 1px 3px rgba(0,0,0,0.02), 0 8px 32px rgba(0,0,0,0.02);
        margin-bottom:24px;
    }
    .cal-month-title {
        font-size:22px; font-weight:800; color:#0f172a;
        letter-spacing:-0.03em; margin-bottom:20px;
    }
    .cal-table {border-collapse:separate; border-spacing:5px; width:100%; text-align:center; font-family:Inter,sans-serif;}
    .cal-table th {
        padding:10px 4px; font-size:9px; font-weight:800; color:#94a3b8;
        text-transform:uppercase; letter-spacing:0.14em;
    }
    .cal-table td {
        padding:10px 6px; border-radius:14px; vertical-align:top; min-width:100px;
        background:#f8fafc; border:1.5px solid #f1f5f9;
        transition:all 0.2s cubic-bezier(0.4,0,0.2,1);
    }
    .cal-table td:hover {
        background:#fff; border-color:#e2e8f0;
        box-shadow:0 2px 12px rgba(0,0,0,0.04);
        transform:translateY(-1px);
    }
    .cal-day-num {font-weight:800; font-size:15px; color:#334155; margin-bottom:6px; letter-spacing:-0.02em;}
    .cal-past {color:#cbd5e1 !important; font-weight:400;}
    .cal-bench {font-weight:800; font-size:12px; letter-spacing:-0.01em;}
    .cal-comp {font-weight:800; font-size:12px; letter-spacing:-0.01em;}
    .cal-min {font-size:9px; font-weight:600; opacity:0.5; margin-left:1px;}
    .cal-booked {
        font-size:8px; font-weight:800; letter-spacing:0.08em;
        text-transform:uppercase; padding:2px 6px; border-radius:4px;
        display:inline-block; margin-top:1px;
    }
    .cal-cheaper-bench {background:#ecfdf5 !important; border-color:#a7f3d0 !important;}
    .cal-cheaper-comp {background:#fff1f2 !important; border-color:#fecdd3 !important;}
    .cal-same {background:#f8fafc !important; border-color:#e2e8f0 !important;}
    .cal-today {border-color:#6366f1 !important; border-width:2px !important;}

    /* ── Legend bar ── */
    .legend-bar {
        display:flex; flex-wrap:wrap; gap:16px; align-items:center;
        padding:14px 20px; border-radius:16px;
        background:#f8fafc; border:1px solid #f1f5f9;
        font-size:12px; font-weight:500; color:#64748b;
        margin-bottom:24px;
    }
    .legend-dot {width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px;}
    .legend-tag {
        padding:3px 10px; border-radius:8px; font-size:11px; font-weight:700;
        letter-spacing:0.02em;
    }

    /* ── Dataframe ── */
    .stDataFrame {border-radius:16px !important; overflow:hidden;}
    .stDataFrame [data-testid="stDataFrameResizable"] {border-radius:16px; border:1px solid #f1f5f9;}

    /* ── Progress bar ── */
    .stProgress > div > div > div {background:#6366f1 !important; border-radius:100px;}
</style>
""", unsafe_allow_html=True)


# ── Saved competitors (per-property) ──────────────────────

def _load_all_saved() -> dict[str, list[dict]]:
    if SAVED_FILE.exists():
        data = json.loads(SAVED_FILE.read_text())
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


# ── Hero ──────────────────────────────────────────────────

st.markdown("""
<div class="hero fade-in">
    <h1>Airbnb Benchmark</h1>
    <p>Confronta i prezzi delle tue property con i competitor nei prossimi 120 giorni</p>
    <div class="hero-badge">
        <span class="dot"></span>
        Dati in tempo reale via Airbnb API
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

# ── Fetch data ─────────────────────────────────────────────


def _fetch_property(listing_id: str, n_calls: int, months: int = 4) -> dict:
    today = date.today()
    cal_days = fetch_calendar(listing_id, today.month, today.year, count=months)
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
    bench_data = _fetch_property(bench["listing_id"], max_price_calls, months_ahead)
    progress.progress(50, text="Scaricamento competitor...")
    comp_data = _fetch_property(comp_id, max_price_calls, months_ahead)
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
    html += f'<div class="cal-month-title">{month_name} {year}</div>'

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
<div style="text-align:center;padding:48px 0 0;font-size:11px;font-weight:500;color:#cbd5e1;
            letter-spacing:0.02em;">
    Airbnb Benchmark · Dati via Airbnb Internal API · Prezzi in EUR
</div>
""", unsafe_allow_html=True)
