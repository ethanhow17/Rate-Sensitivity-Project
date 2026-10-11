import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Mortgage Rate Sensitivity Monitor", layout="wide")


# ---------- Load data ----------
@st.cache_data(ttl=60 * 60 * 12)  # refresh FRED data at most every 12 hours
def load_rates():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
    df = pd.read_csv(url)
    df.columns = ["date", "rate"]
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_loans():
    df = pd.read_csv("loan_summary.csv")
    df["year"] = df["year"].astype(str)
    return df


rates = load_rates()
loans = load_loans()
market_rate = float(rates["rate"].iloc[-1])
as_of = rates["date"].iloc[-1].strftime("%b %d, %Y")

# ---------- Header ----------
st.title("Mortgage Rate Sensitivity Monitor")
st.caption(
    f"30-year mortgage rate as of {as_of} (Freddie Mac, via FRED). "
    "Loans: HMDA first-lien home loans originated in California."
)

# ---------- Sidebar controls ----------
st.sidebar.header("Settings")
all_years = sorted(loans["year"].unique())
all_types = sorted(loans["loan_type"].dropna().unique())

years = st.sidebar.multiselect("Origination years", all_years, default=all_years)
types = st.sidebar.multiselect("Loan types", all_types, default=all_types)
shock = st.sidebar.slider("Rate shock (%)", -2.0, 2.0, 0.0, 0.125)
threshold = st.sidebar.slider("Refinance threshold (%)", 0.25, 1.0, 0.5, 0.125,
                              help="How much lower the market rate must be before a borrower refinances.")

data = loans[loans["year"].isin(years) & loans["loan_type"].isin(types)]
if data.empty:
    st.warning("Select at least one year and one loan type.")
    st.stop()


def share_in_money(df, rate):
    total = df["loans"].sum()
    in_money = df.loc[df["rate_bucket"] - rate >= threshold, "loans"].sum()
    return in_money / total if total else 0


shocked_rate = market_rate + shock
base_share = share_in_money(data, market_rate)
new_share = share_in_money(data, shocked_rate)

# ---------- Headline numbers ----------
c1, c2, c3 = st.columns(3)
c1.metric("Current 30-year rate", f"{market_rate:.2f}%")
c2.metric("Loans in the money today", f"{base_share:.1%}")
c3.metric(f"In the money at {shocked_rate:.2f}%", f"{new_share:.1%}",
          delta=f"{(new_share - base_share) * 100:+.1f} pts")

# ---------- Charts ----------
left, right = st.columns(2)

with left:
    st.subheader("30-year mortgage rate, last 5 years")
    recent = rates[rates["date"] >= rates["date"].max() - pd.DateOffset(years=5)]
    st.line_chart(recent, x="date", y="rate")

with right:
    st.subheader("In-the-money share vs. rate shock")
    shocks = [s / 8 for s in range(-16, 17)]  # -2% to +2% in 1/8 steps
    curve = pd.DataFrame({
        "rate_shock_pct": shocks,
        "in_the_money_pct": [share_in_money(data, market_rate + s) * 100 for s in shocks],
    })
    st.line_chart(curve, x="rate_shock_pct", y="in_the_money_pct")

st.subheader("Where loan rates sit relative to the market")
dist = data.groupby("rate_bucket", as_index=False)["loans"].sum()
dist = dist[(dist["rate_bucket"] >= 2) & (dist["rate_bucket"] <= 10)]
bars = alt.Chart(dist).mark_bar().encode(
    x=alt.X("rate_bucket:Q", title="Loan interest rate (%)"),
    y=alt.Y("loans:Q", title="Number of loans"),
)
cutoff = alt.Chart(pd.DataFrame({"x": [shocked_rate + threshold]})).mark_rule(
    color="red", strokeWidth=2
).encode(x="x:Q")
st.altair_chart(bars + cutoff)
st.caption("Loans to the right of the red line are in the money at the selected rate.")

# ---------- By origination year ----------
st.subheader("By origination year")
by_year = pd.DataFrame([
    {"Year": y, "In the money today": share_in_money(g, market_rate),
     f"At {shocked_rate:.2f}%": share_in_money(g, shocked_rate)}
    for y, g in data.groupby("year")
])
st.dataframe(by_year.style.format({c: "{:.1%}" for c in by_year.columns if c != "Year"}),
             hide_index=True)

# ---------- What this means ----------
st.subheader("What this shows")
st.markdown(
    """
A loan is **in the money** when market rates fall far enough below its rate that the borrower
would likely refinance. Refinancing boosts origination volume for lenders but pays off existing
loans, reducing the value of mortgage servicing rights (MSRs). Because loan rates cluster in a
narrow range, refinance exposure grows sharply once rates fall below that cluster, while rising
rates change little.

**Limitations:** FRED's rate is a survey average for prime conventional loans; FHA and VA loans
price differently. The refinance threshold is a simplified rule of thumb, and HMDA shows when
loans were made, not whether they have since been paid off.
"""
)