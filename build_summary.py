import duckdb
import pandas as pd

# 1. Filter and summarize loans from all years
loans = duckdb.sql("""
    SELECT
        activity_year AS year,
        CASE loan_type
            WHEN '1' THEN 'Conventional'
            WHEN '2' THEN 'FHA'
            WHEN '3' THEN 'VA'
            WHEN '4' THEN 'USDA'
        END AS loan_type,
        ROUND(TRY_CAST(interest_rate AS DOUBLE) * 8) / 8 AS rate_bucket,
        COUNT(*) AS loans
    FROM read_csv('HMDA_*_CA.csv', all_varchar = true, union_by_name = true)
    WHERE lien_status = '1'                       -- first mortgages only
      AND "open-end_line_of_credit" = '2'         -- no home equity lines
      AND reverse_mortgage = '2'                  -- no reverse mortgages
      AND business_or_commercial_purpose = '2'    -- personal loans only
      AND TRY_CAST(interest_rate AS DOUBLE) BETWEEN 1 AND 15  -- drop bad values
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
""").df()

loans.to_csv("loan_summary.csv", index=False)
print("Loans kept by year:")
print(loans.groupby("year")["loans"].sum())

# 2. Get today's mortgage rate from FRED
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
rates = pd.read_csv(url)
rates.columns = ["date", "rate"]
market_rate = rates["rate"].iloc[-1]
print("\nCurrent 30-year rate:", market_rate)

# 3. In-the-money share by year, at today's rate and under rate shocks
threshold = 0.5

for year, group in loans.groupby("year"):
    total = group["loans"].sum()
    print(f"\n{year} loans:")
    for shock in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        new_rate = market_rate + shock
        in_money = group[group["rate_bucket"] - new_rate >= threshold]["loans"].sum()
        print(f"  Rates {shock:+.1f}% -> {new_rate:.2f}%: {in_money / total:.1%} in the money")