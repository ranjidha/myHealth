from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# -----------------------------
# Google Sheet (Published CSV)
# -----------------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT3o-k1EL_KIcflUTbZrW2DIGUgJXRhdtfvtyYQ5G4-G_HPmEm5tThVfZL5jVHJa7LtwCdbMs30hV2j/pub?output=csv"

EXPECTED_COLUMNS = [
    "date",
    "weight_lbs",
    "surya_namaskar",
    "water_glasses_8oz",
    "fasting_window_hours",
    "breakfast",
    "lunch",
    "dinner",
    "snacks",
    "notes",
]

def _to_int_safe(x, default=0) -> int:
    """Convert x to int safely, returning default on NaN/blank/bad values."""
    if x is None:
        return default
    if isinstance(x, (int, np.integer)):
        return int(x)
    try:
        # Handle strings like "" or "  "
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return default
        return int(float(s))  # handles "24.0"
    except Exception:
        return default

def _to_float_safe(x) -> float:
    """Convert x to float safely, returning NaN if invalid."""
    try:
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

@st.cache_data(ttl=300)
def load_data_from_sheet() -> pd.DataFrame:
    df = pd.read_csv(SHEET_CSV_URL)
    df.columns = [c.strip() for c in df.columns]

    # Ensure all expected columns exist (create empty if missing)
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"]).copy()

    # Clean numeric columns (handle blanks/strings)
    df["weight_lbs"] = df["weight_lbs"].apply(_to_float_safe)
    df["surya_namaskar"] = df["surya_namaskar"].apply(_to_int_safe)
    df["water_glasses_8oz"] = df["water_glasses_8oz"].apply(_to_int_safe)
    df["fasting_window_hours"] = df["fasting_window_hours"].apply(_to_int_safe)

    # Ensure text columns are strings
    for col in ["breakfast", "lunch", "dinner", "snacks", "notes"]:
        df[col] = df[col].fillna("").astype(str)

    return df.sort_values("date")

# -----------------------------
# Page
# -----------------------------
st.set_page_config(page_title="Daily Health Log Dashboard", layout="wide")
st.title("Daily Health Log Dashboard")
st.caption("Read-only dashboard (data is fetched from Google Sheets CSV).")

df = load_data_from_sheet()

# -----------------------------
# Sidebar (read-only)
# -----------------------------
st.sidebar.header("Daily Log (Read-only)")

default_date = date.today()
selected_date = st.sidebar.date_input("Date", value=default_date)

prefill = {}
if len(df) > 0 and (df["date"] == selected_date).any():
    prefill = df[df["date"] == selected_date].iloc[0].to_dict()

weight_lbs = st.sidebar.text_input("Weight (lbs)", value=str(prefill.get("weight_lbs", "")))

# ✅ FIX: safe conversion even if blank/NaN/string
surya_default = _to_int_safe(prefill.get("surya_namaskar", 0), default=0)
water_default = _to_int_safe(prefill.get("water_glasses_8oz", 0), default=0)
fasting_default = _to_int_safe(prefill.get("fasting_window_hours", 0), default=0)

surya = st.sidebar.number_input("Surya Namaskar (count)", min_value=0, max_value=500, value=surya_default)
water = st.sidebar.number_input("Water (8oz glasses)", min_value=0, max_value=40, value=water_default)
fasting = st.sidebar.number_input("Fasting window (hours)", min_value=0, max_value=24, value=fasting_default)

st.sidebar.subheader("Meals (free text)")
st.sidebar.text_area("Breakfast", value=prefill.get("breakfast", ""), height=80, disabled=True)
st.sidebar.text_area("Lunch", value=prefill.get("lunch", ""), height=80, disabled=True)
st.sidebar.text_area("Dinner", value=prefill.get("dinner", ""), height=80, disabled=True)
st.sidebar.text_area("Snacks", value=prefill.get("snacks", ""), height=80, disabled=True)
st.sidebar.text_area("Notes", value=prefill.get("notes", ""), height=80, disabled=True)

st.sidebar.info("Saving/editing from the app is disabled because CSV access is read-only. Update the Google Sheet directly.")

# -----------------------------
# Top metrics
# -----------------------------
left, mid, right, fourth = st.columns(4)

if len(df) == 0:
    left.metric("Entries", "0")
    st.info("No rows found in your Google Sheet (or it is not published as CSV).")
    st.stop()

df_show = df.copy()
df_show["date"] = pd.to_datetime(df_show["date"])

entries = len(df_show)
latest = df_show.sort_values("date").iloc[-1]
first = df_show.sort_values("date").iloc[0]

left.metric("Entries logged", f"{entries}")

# Weight delta
w_latest = latest["weight_lbs"]
w_first = first["weight_lbs"]
if pd.notna(w_latest) and pd.notna(w_first):
    delta = w_latest - w_first
    mid.metric("Weight (latest)", f"{w_latest:.1f} lbs", f"{delta:+.1f} lbs")
else:
    mid.metric("Weight (latest)", "—", "Add weight to track")

right.metric("Surya Namaskar (latest)", f"{int(latest['surya_namaskar'])}")
fourth.metric("Water (latest)", f"{int(latest['water_glasses_8oz'])} glasses")

st.divider()

# -----------------------------
# Filters
# -----------------------------
with st.expander("Filters"):
    min_d = df_show["date"].min().date()
    max_d = df_show["date"].max().date()
    start_d, end_d = st.date_input("Date range", value=(min_d, max_d))
    mask = (df_show["date"].dt.date >= start_d) & (df_show["date"].dt.date <= end_d)
    df_f = df_show.loc[mask].sort_values("date")
    st.caption(f"Showing {len(df_f)} entries from {start_d} to {end_d}")

# -----------------------------
# Charts
# -----------------------------
c1, c2 = st.columns(2)

def line_chart(dfx, y_col, title, y_label):
    fig = plt.figure()
    x = dfx["date"]
    y = dfx[y_col]
    plt.plot(x, y, marker="o")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel(y_label)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)

with c1:
    st.subheader("Weight trend")
    if df_f["weight_lbs"].notna().sum() >= 2:
        line_chart(df_f.dropna(subset=["weight_lbs"]), "weight_lbs", "Weight (lbs) over time", "lbs")
    else:
        st.info("Add weight for at least 2 days to show the trend.")

with c2:
    st.subheader("Surya Namaskar trend")
    line_chart(df_f, "surya_namaskar", "Surya Namaskar (count) over time", "count")

c3, c4 = st.columns(2)

with c3:
    st.subheader("Water intake trend")
    line_chart(df_f, "water_glasses_8oz", "Water (8oz glasses) over time", "glasses")

with c4:
    st.subheader("Fasting window trend")
    line_chart(df_f, "fasting_window_hours", "Fasting window (hours) over time", "hours")

st.divider()

# -----------------------------
# Table + export
# -----------------------------
st.subheader("Your logged entries")
st.dataframe(df_f.sort_values("date", ascending=False), use_container_width=True)

csv_bytes = df_f.copy()
csv_bytes["date"] = csv_bytes["date"].dt.strftime("%Y-%m-%d")
st.download_button(
    "Download filtered data as CSV",
    data=csv_bytes.to_csv(index=False).encode("utf-8"),
    file_name="health_log_filtered.csv",
    mime="text/csv",
)
