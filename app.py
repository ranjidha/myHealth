import os
from datetime import date, datetime

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt



SHEET_CSV_URL = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vT3o-k1EL_KIcflUTbZrW2DIGUgJXRhdtfvtyYQ5G4-G_HPmEm5tThVfZL5jVHJa7LtwCdbMs30hV2j/pub?output=csv")

@st.cache_data(ttl=300)
def load_data_from_sheet():
    df = pd.read_csv(SHEET_CSV_URL)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date")
"""
 DATA_FILE = "data.csv"
# -----------------------------
# Helpers
# -----------------------------
COLUMNS = [
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

def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # Ensure date parsing
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df.sort_values("date")
    return pd.DataFrame(columns=COLUMNS)
    """

def save_data(df: pd.DataFrame):
    # store dates as ISO strings
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_FILE, index=False)

def upsert_row(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    # replace if date already exists
    d = row["date"]
    if len(df) > 0 and (df["date"] == d).any():
        df = df[df["date"] != d]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return df.sort_values("date")

def safe_float(x):
    try:
        return float(x)
    except:
        return np.nan

def safe_int(x):
    try:
        return int(x)
    except:
        return np.nan

# -----------------------------
# Page
# -----------------------------
st.set_page_config(page_title="Daily Health Log Dashboard", layout="wide")
st.title("Daily Health Log Dashboard")
st.caption("Log your daily meals + Surya Namaskar + water + weight, and track progress with charts.")

df = load_data()

# -----------------------------
# Sidebar input form
# -----------------------------
st.sidebar.header("Add / Update Daily Log")

default_date = date.today()
selected_date = st.sidebar.date_input("Date", value=default_date)

# If there is an existing row for that date, prefill
prefill = {}
if len(df) > 0 and (df["date"] == selected_date).any():
    prefill = df[df["date"] == selected_date].iloc[0].to_dict()

weight_lbs = st.sidebar.text_input("Weight (lbs)", value=str(prefill.get("weight_lbs", "")))
surya = st.sidebar.number_input("Surya Namaskar (count)", min_value=0, max_value=500, value=int(prefill.get("surya_namaskar", 0) or 0))
water = st.sidebar.number_input("Water (8oz glasses)", min_value=0, max_value=40, value=int(prefill.get("water_glasses_8oz", 0) or 0))
fasting = st.sidebar.number_input("Fasting window (hours)", min_value=0, max_value=24, value=int(prefill.get("fasting_window_hours", 0) or 0))

st.sidebar.subheader("Meals (free text)")
breakfast = st.sidebar.text_area("Breakfast", value=prefill.get("breakfast", ""), height=80)
lunch = st.sidebar.text_area("Lunch", value=prefill.get("lunch", ""), height=80)
dinner = st.sidebar.text_area("Dinner", value=prefill.get("dinner", ""), height=80)
snacks = st.sidebar.text_area("Snacks", value=prefill.get("snacks", ""), height=80)
notes = st.sidebar.text_area("Notes", value=prefill.get("notes", ""), height=80)

if st.sidebar.button("Save entry", type="primary"):
    row = {
        "date": selected_date,
        "weight_lbs": safe_float(weight_lbs),
        "surya_namaskar": safe_int(surya),
        "water_glasses_8oz": safe_int(water),
        "fasting_window_hours": safe_int(fasting),
        "breakfast": breakfast.strip(),
        "lunch": lunch.strip(),
        "dinner": dinner.strip(),
        "snacks": snacks.strip(),
        "notes": notes.strip(),
    }
    df = upsert_row(df, row)
    save_data(df)
    st.sidebar.success(f"Saved for {selected_date} ✅")

st.sidebar.divider()

# -----------------------------
# Top metrics
# -----------------------------
left, mid, right, fourth = st.columns(4)

if len(df) == 0:
    left.metric("Entries", "0")
    st.info("Add your first entry from the sidebar to start seeing charts.")
    st.stop()

df_show = df.copy()
df_show["date"] = pd.to_datetime(df_show["date"])

entries = len(df_show)
latest = df_show.sort_values("date").iloc[-1]
first = df_show.sort_values("date").iloc[0]

left.metric("Entries logged", f"{entries}")

# Weight delta (if weight exists)
w_latest = latest["weight_lbs"]
w_first = first["weight_lbs"]
if pd.notna(w_latest) and pd.notna(w_first):
    delta = w_latest - w_first
    mid.metric("Weight (latest)", f"{w_latest:.1f} lbs", f"{delta:+.1f} lbs")
else:
    mid.metric("Weight (latest)", "—", "Add weight to track")

# Surya
surya_latest = latest["surya_namaskar"]
third_val = int(surya_latest) if pd.notna(surya_latest) else 0
right.metric("Surya Namaskar (latest)", f"{third_val}")

# Water
water_latest = latest["water_glasses_8oz"]
fourth_val = int(water_latest) if pd.notna(water_latest) else 0
fourth.metric("Water (latest)", f"{fourth_val} glasses")

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
    if df_f["surya_namaskar"].notna().sum() >= 1:
        line_chart(df_f, "surya_namaskar", "Surya Namaskar (count) over time", "count")
    else:
        st.info("Add Surya Namaskar counts to see this chart.")

c3, c4 = st.columns(2)

with c3:
    st.subheader("Water intake trend")
    if df_f["water_glasses_8oz"].notna().sum() >= 1:
        line_chart(df_f, "water_glasses_8oz", "Water (8oz glasses) over time", "glasses")
    else:
        st.info("Add water glasses to see this chart.")

with c4:
    st.subheader("Fasting window trend")
    if df_f["fasting_window_hours"].notna().sum() >= 1:
        line_chart(df_f, "fasting_window_hours", "Fasting window (hours) over time", "hours")
    else:
        st.info("Add fasting window hours to see this chart.")

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

# -----------------------------
# Delete entry (optional)
# -----------------------------
with st.expander("Delete an entry"):
    del_date = st.date_input("Select date to delete", value=df_show["date"].max().date(), key="delete_date")
    if st.button("Delete this date"):
        before = len(df)
        df2 = df[df["date"] != del_date].copy()
        if len(df2) == before:
            st.warning("No entry found for that date.")
        else:
            df = df2
            save_data(df)
            st.success(f"Deleted entry for {del_date}.")
