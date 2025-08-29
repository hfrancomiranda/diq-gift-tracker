"""
DIQ Gift Tracker — MINIMAL VERSION
----------------------------------
Keep-it-simple Streamlit app to track gifts. One page, one table, one form.

Run locally:
  pip install streamlit pandas
  streamlit run gift_tracker_app_min.py

What’s included:
- Add gifts via a small form
- View/filter table
- Mark purchased + track cost
- Import/Export CSV (for safekeeping)

What’s NOT included (to stay simple):
- Collector mode / public form
- Charts, priorities, notes, links, XLSX export
- Fancy type juggling — we coerce numbers safely
"""
from __future__ import annotations
import io
from datetime import date, datetime
import pandas as pd
import streamlit as st

APP_TITLE = "🎁 DIQ Gift Tracker (Simple)"

# Minimal schema
COLUMNS = [
    "date", "year", "recipient", "occasion", "idea",
    "budget", "purchased", "purchased_cost"
]

# ---------- helpers ----------

def empty_df() -> pd.DataFrame:
    df = pd.DataFrame(columns=COLUMNS)
    df["date"] = pd.Series(dtype=str)
    df["year"] = pd.Series(dtype=int)
    df["recipient"] = pd.Series(dtype=str)
    df["occasion"] = pd.Series(dtype=str)
    df["idea"] = pd.Series(dtype=str)
    df["budget"] = pd.Series(dtype=float)
    df["purchased"] = pd.Series(dtype=bool)
    df["purchased_cost"] = pd.Series(dtype=float)
    return df


def ensure_df(df: pd.DataFrame) -> pd.DataFrame:
    # add missing
    for c in COLUMNS:
        if c not in df.columns:
            if c in ("budget", "purchased_cost"):
                df[c] = 0.0
            elif c == "purchased":
                df[c] = False
            elif c == "year":
                df[c] = datetime.now().year
            elif c == "date":
                df[c] = date.today().isoformat()
            else:
                df[c] = ""
    # coerce types safely
    df = df[COLUMNS].copy()
    df["date"] = df["date"].fillna("").astype(str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(datetime.now().year).astype(int)
    for col in ("budget", "purchased_cost"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
    df["purchased"] = df["purchased"].fillna(False).astype(bool)
    for col in ("recipient", "occasion", "idea"):
        df[col] = df[col].fillna("").astype(str)
    return df


def download_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ---------- app ----------

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🎁", layout="centered")
    st.title(APP_TITLE)

    # init state
    if "gifts" not in st.session_state:
        st.session_state.gifts = ensure_df(empty_df())

    # sidebar: import/export + quick totals
    st.sidebar.header("Data")
    up = st.sidebar.file_uploader("Import CSV", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up)
            st.session_state.gifts = ensure_df(df)
            st.sidebar.success("Imported.")
        except Exception as e:
            st.sidebar.error(f"Upload failed: {e}")

    if not st.session_state.gifts.empty:
        st.sidebar.download_button(
            "Export CSV",
            data=download_csv(st.session_state.gifts),
            file_name="gifts.csv",
            mime="text/csv",
        )

    # filters
    df = st.session_state.gifts.copy()
    years = sorted(df["year"].unique().tolist()) if not df.empty else [datetime.now().year]
    c1, c2 = st.columns(2)
    with c1:
        f_year = st.multiselect("Year", years, default=years)
        f_rec = st.text_input("Recipient contains", "").strip().lower()
    with c2:
        f_occ = st.text_input("Occasion contains", "").strip().lower()
        show_only_unpurchased = st.checkbox("Show only unpurchased", value=False)

    mask = df["year"].isin(f_year)
    if f_rec:
        mask &= df["recipient"].str.lower().str.contains(f_rec, na=False)
    if f_occ:
        mask &= df["occasion"].str.lower().str.contains(f_occ, na=False)
    if show_only_unpurchased:
        mask &= ~df["purchased"]

    fdf = df.loc[mask].copy()

    # KPIs
    total_budget = float(fdf["budget"].sum())
    total_spent = float(fdf.loc[fdf["purchased"], "purchased_cost"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Budget", f"${total_budget:,.2f}")
    c2.metric("Spent", f"${total_spent:,.2f}")
    c3.metric("Remaining", f"${max(total_budget-total_spent, 0.0):,.2f}")

    # add form (simple)
    st.subheader("Add a gift")
    with st.form("add_gift", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dt_val = st.date_input("Date", value=date.today())
            year_val = st.number_input("Year", min_value=2000, max_value=2100, value=date.today().year)
            recipient = st.text_input("Recipient")
        with col2:
            occasion = st.text_input("Occasion")
            idea = st.text_input("Idea")
            budget = st.number_input("Budget", min_value=0.0, step=1.0)
        col3, col4 = st.columns(2)
        with col3:
            purchased = st.checkbox("Purchased?", value=False)
        with col4:
            purchased_cost = st.number_input("Purchased Cost", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Add")

    if submitted:
        new_row = {
            "date": dt_val.isoformat(),
            "year": int(year_val),
            "recipient": recipient.strip(),
            "occasion": occasion.strip(),
            "idea": idea.strip(),
            "budget": float(budget or 0.0),
            "purchased": bool(purchased),
            "purchased_cost": float(purchased_cost or 0.0),
        }
        st.session_state.gifts = ensure_df(pd.concat([st.session_state.gifts, pd.DataFrame([new_row])], ignore_index=True))
        st.success("Added.")

    # table (editable for purchased & cost only, to keep UI simple)
    st.subheader("Gifts")
    if fdf.empty:
        st.info("No gifts yet — add one above or import a CSV.")
    else:
        edit_cols = ["purchased", "purchased_cost"]
        st.caption("Tip: You can edit Purchased and Purchased Cost inline.")
        edited = st.data_editor(
            fdf,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "purchased": st.column_config.CheckboxColumn("Purchased"),
                "purchased_cost": st.column_config.NumberColumn("Purchased Cost", min_value=0.0, step=1.0),
            },
            disabled=[c for c in fdf.columns if c not in edit_cols],
            key="editor",
        )
        # write back edited rows into main df
        st.session_state.gifts.loc[edited.index, edit_cols] = edited[edit_cols]


if __name__ == "__main__":
    main()
