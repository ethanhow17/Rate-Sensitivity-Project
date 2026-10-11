import duckdb

file = "HMDA_2025_CA.csv"

print(duckdb.sql(f"""
    SELECT
        activity_year,
        COUNT(*) AS loans,
        ROUND(AVG(TRY_CAST(interest_rate AS DOUBLE)), 2) AS avg_rate
    FROM read_csv('{file}', all_varchar = true)
    GROUP BY activity_year
"""))