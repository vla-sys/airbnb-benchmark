"""Price tracker page — historical price charts and comparison table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db.models import init_db
from db.queries import get_my_properties, get_competitors, get_latest_prices

init_db()

st.set_page_config(page_title="Price Tracker", page_icon="💰", layout="wide")
st.title("💰 Price Tracker")

# ── Property selector ───────────────────────────────────────

properties = get_my_properties()
prop_names = [p["name"] for p in properties]
selected_name = st.selectbox("Property", prop_names)
selected_prop = next(p for p in properties if p["name"] == selected_name)

competitors = get_competitors(selected_prop["id"])

if not competitors:
    st.info(
        "Nessun competitor monitorato. "
        "Vai alla pagina **Gestione Competitor** per aggiungerne."
    )
    st.stop()

# ── Filters ─────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)
with col1:
    date_range = st.selectbox(
        "Periodo",
        ["Prossimi 30 giorni", "Prossimi 60 giorni", "Prossimi 90 giorni"],
        index=0,
    )
    days = {"Prossimi 30 giorni": 30, "Prossimi 60 giorni": 60, "Prossimi 90 giorni": 90}[date_range]

with col2:
    comp_names = [c["name"] for c in competitors]
    selected_comps = st.multiselect(
        "Competitor",
        comp_names,
        default=comp_names,
    )

with col3:
    day_filter = st.selectbox(
        "Giorni",
        ["Tutti", "Solo weekend (Ven-Dom)", "Solo infrasettimanali (Lun-Gio)"],
    )

# Filter competitor IDs
selected_ids = [c["id"] for c in competitors if c["name"] in selected_comps]

if not selected_ids:
    st.warning("Seleziona almeno un competitor.")
    st.stop()

# ── Fetch data ──────────────────────────────────────────────

df = get_latest_prices(selected_ids)

if df.empty:
    st.info(
        "Nessun dato di prezzo disponibile. "
        "Lancia una raccolta dati dalla **Home** o attendi lo scraping automatico."
    )
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# Date filtering
today = pd.Timestamp(date.today())
end_date = today + timedelta(days=days)
df = df[(df["date"] >= today) & (df["date"] <= end_date)]

# Day of week filtering
if day_filter == "Solo weekend (Ven-Dom)":
    df = df[df["date"].dt.dayofweek.isin([4, 5, 6])]
elif day_filter == "Solo infrasettimanali (Lun-Gio)":
    df = df[df["date"].dt.dayofweek.isin([0, 1, 2, 3])]

if df.empty:
    st.info("Nessun dato per i filtri selezionati.")
    st.stop()

st.divider()

# ── Price chart ─────────────────────────────────────────────

st.subheader("Andamento prezzi")

fig = px.line(
    df,
    x="date",
    y="price",
    color="competitor_name",
    labels={"date": "Data", "price": "Prezzo (€)", "competitor_name": "Competitor"},
    template="plotly_white",
)
fig.update_layout(
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

# ── Average price comparison ────────────────────────────────

st.subheader("Prezzo medio per competitor")

avg_df = df.groupby("competitor_name")["price"].mean().reset_index()
avg_df.columns = ["Competitor", "Prezzo medio (€)"]
avg_df["Prezzo medio (€)"] = avg_df["Prezzo medio (€)"].round(2)
avg_df = avg_df.sort_values("Prezzo medio (€)", ascending=False)

col1, col2 = st.columns([2, 1])
with col1:
    fig_bar = px.bar(
        avg_df,
        x="Competitor",
        y="Prezzo medio (€)",
        color="Competitor",
        template="plotly_white",
    )
    fig_bar.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    overall_avg = avg_df["Prezzo medio (€)"].mean()
    st.metric("Media competitor", f"€{overall_avg:.0f}")
    cheapest = avg_df.iloc[-1]
    most_expensive = avg_df.iloc[0]
    st.metric("Più economico", f"€{cheapest['Prezzo medio (€)']:.0f}", cheapest["Competitor"])
    st.metric("Più caro", f"€{most_expensive['Prezzo medio (€)']:.0f}", most_expensive["Competitor"])

# ── Price comparison table ──────────────────────────────────

st.divider()
st.subheader("Tabella comparativa — prossime notti")

pivot = df.pivot_table(
    index="date",
    columns="competitor_name",
    values="price",
    aggfunc="first",
)
pivot.index = pivot.index.strftime("%d/%m (%a)")

# Add average column
pivot["MEDIA"] = pivot.mean(axis=1).round(0)

st.dataframe(
    pivot.style.format("€{:.0f}", na_rep="—").background_gradient(
        cmap="RdYlGn_r", axis=None, subset=pivot.columns[:-1]
    ),
    use_container_width=True,
    height=min(len(pivot) * 35 + 40, 600),
)

# ── Price alerts ────────────────────────────────────────────

st.divider()
st.subheader("⚠️ Segnalazioni")

if len(avg_df) > 1:
    avg_price = avg_df["Prezzo medio (€)"].mean()
    for _, row in avg_df.iterrows():
        diff_pct = ((row["Prezzo medio (€)"] - avg_price) / avg_price) * 100
        if diff_pct > 20:
            st.warning(
                f"**{row['Competitor']}** è {diff_pct:.0f}% sopra la media "
                f"(€{row['Prezzo medio (€)']:.0f} vs €{avg_price:.0f})"
            )
        elif diff_pct < -20:
            st.info(
                f"**{row['Competitor']}** è {abs(diff_pct):.0f}% sotto la media "
                f"(€{row['Prezzo medio (€)']:.0f} vs €{avg_price:.0f})"
            )
