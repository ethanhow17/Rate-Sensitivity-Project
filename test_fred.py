import pandas as pd

url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
rates = pd.read_csv(url)
rates.columns = ["date", "rate"]
print(rates.tail())
