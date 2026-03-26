"""Availability calendar page — heatmap and occupancy insights."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
import calendar

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db.models import init_db
from db.queries import get_my_properties, get_competitors, get_availability

init_db()

st.set_page_config(page_title="Disponibilità", page_icon="📅", layout="wide")
st.title("📅 Disponibilità Competitor")

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

col1, col2 = st.columns(2)
with col1:
    months_ahead = st.selectbox("Mostra", ["1 mese", "2 mesi", "3 mesi"], index=1)
    n_months = {"1 mese": 1, "2 mesi": 2, "3 mesi": 3}[months_ahead]

with col2:
    comp_names = [c["name"] for c in competitors]
    selected_comps = st.multiselect(
        "Competitor", comp_names, default=comp_names
    )

selected_ids = [c["id"] for c in competitors if c["name"] in selected_comps]

if not selected_ids:
    st.warning("Seleziona almeno un competitor.")
    st.stop()

# ── Fetch data ──────────────────────────────────────────────

today = date.today()
end_date = today + timedelta(days=n_months * 31)

df = get_availability(selected_ids, date_from=today, date_to=end_date)

if df.empty:
    st.info(
        "Nessun dato di disponibilità. "
        "Lancia una raccolta dati dalla **Home** o attendi lo scraping automatico."
    )
    st.stop()

df["date"] = pd.to_datetime(df["date"])

st.divider()

# ── Occupancy heatmap ───────────────────────────────────────

st.subheader("Mappa occupazione")
st.caption("🟢 Disponibile · 🔴 Occupato · ⬜ Nessun dato")

# Create a matrix: rows = competitors, columns = dates
pivot = df.pivot_table(
    index="competitor_name",
    columns="date",
    values="is_available",
    aggfunc="first",
)

# Sort dates
pivot = pivot.reindex(sorted(pivot.columns), axis=1)

# Create heatmap
z_values = pivot.values.astype(float)
# Invert: 0 = booked (red), 1 = available (green)
z_display = np.where(np.isnan(z_values), 0.5, 1 - z_values)

date_labels = [d.strftime("%d/%m") for d in pivot.columns]

fig = go.Figure(
    data=go.Heatmap(
        z=z_display,
        x=date_labels,
        y=pivot.index.tolist(),
        colorscale=[[0, "#2ecc71"], [0.5, "#ecf0f1"], [1, "#e74c3c"]],
        showscale=False,
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata}<extra></extra>",
        customdata=np.where(
            np.isnan(z_values),
            "Nessun dato",
            np.where(z_values == 1, "Disponibile", "Occupato"),
        ),
    )
)

fig.update_layout(
    height=max(200, len(pivot) * 40 + 100),
    xaxis=dict(title="Data", side="top", tickangle=-45),
    yaxis=dict(title="", autorange="reversed"),
    template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

# ── Occupancy rate per competitor ───────────────────────────

st.divider()
st.subheader("Tasso di occupazione")

occ_df = df.groupby("competitor_name")["is_available"].agg(
    total="count",
    available="sum",
).reset_index()
occ_df["booked"] = occ_df["total"] - occ_df["available"]
occ_df["occupancy_pct"] = ((occ_df["booked"] / occ_df["total"]) * 100).round(1)
occ_df = occ_df.sort_values("occupancy_pct", ascending=False)

col1, col2 = st.columns([2, 1])

with col1:
    fig_occ = go.Figure()
    fig_occ.add_trace(
        go.Bar(
            x=occ_df["competitor_name"],
            y=occ_df["occupancy_pct"],
            marker_color=["#e74c3c" if v > 70 else "#f39c12" if v > 40 else "#2ecc71" for v in occ_df["occupancy_pct"]],
            text=[f"{v}%" for v in occ_df["occupancy_pct"]],
            textposition="auto",
        )
    )
    fig_occ.update_layout(
        yaxis=dict(title="% Occupazione", range=[0, 100]),
        xaxis=dict(title=""),
        template="plotly_white",
        showlegend=False,
        height=350,
    )
    st.plotly_chart(fig_occ, use_container_width=True)

with col2:
    avg_occ = occ_df["occupancy_pct"].mean()
    st.metric("Occupazione media", f"{avg_occ:.0f}%")
    if not occ_df.empty:
        most_booked = occ_df.iloc[0]
        least_booked = occ_df.iloc[-1]
        st.metric("Più occupato", f"{most_booked['occupancy_pct']}%", most_booked["competitor_name"])
        st.metric("Più libero", f"{least_booked['occupancy_pct']}%", least_booked["competitor_name"])

# ── Insights ────────────────────────────────────────────────

st.divider()
st.subheader("💡 Insight")

# Weekend occupancy
if not df.empty:
    df_weekends = df[df["date"].dt.dayofweek.isin([4, 5, 6])]
    if not df_weekends.empty:
        weekend_occ = ((1 - df_weekends["is_available"].mean()) * 100)
        if weekend_occ > 80:
            st.success(
                f"**{weekend_occ:.0f}%** dei competitor sono occupati nei weekend → "
                f"Alta domanda, puoi alzare il prezzo weekend."
            )
        elif weekend_occ > 50:
            st.info(
                f"**{weekend_occ:.0f}%** dei competitor occupati nei weekend → "
                f"Domanda moderata."
            )
        else:
            st.warning(
                f"Solo **{weekend_occ:.0f}%** dei competitor occupati nei weekend → "
                f"Bassa domanda, valuta promozioni."
            )

    # Find dates where most competitors are booked
    date_occ = df.groupby("date")["is_available"].agg(
        total="count", available="sum"
    ).reset_index()
    date_occ["booked_pct"] = ((1 - date_occ["available"] / date_occ["total"]) * 100).round(0)

    hot_dates = date_occ[date_occ["booked_pct"] >= 80]
    if not hot_dates.empty:
        hot_str = ", ".join(hot_dates["date"].dt.strftime("%d/%m").tolist()[:10])
        st.success(
            f"**Date calde** (≥80% competitor occupati): {hot_str} → "
            f"Assicurati di avere prezzi premium per queste date."
        )

    cold_dates = date_occ[date_occ["booked_pct"] <= 20]
    if not cold_dates.empty:
        cold_str = ", ".join(cold_dates["date"].dt.strftime("%d/%m").tolist()[:10])
        st.warning(
            f"**Date fredde** (≤20% competitor occupati): {cold_str} → "
            f"Valuta promozioni o sconti last-minute."
        )
