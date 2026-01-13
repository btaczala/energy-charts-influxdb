import argparse
import os
import matplotlib.pyplot as plt
import pandas as pd
import requests

parser = argparse.ArgumentParser(description="Fetch and plot energy prices")
parser.add_argument(
    "--year",
    type=int,
    default=int(os.getenv("YEAR", "2023")),
    help="Year to plot",
)
parser.add_argument(
    "--bzn",
    type=str,
    default=os.getenv("BZN", "DE-LU"),
    help="Bidding zone",
)
args = parser.parse_args()

year = args.year
start_date = f"{year}-01-01"
end_date = f"{year}-12-31"
bzn = args.bzn

# Fetch day-ahead prices from energy-charts.info API
url = "https://api.energy-charts.info/price"
params = {"bzn": bzn, "start": start_date, "end": end_date}
response = requests.get(url, params=params)
data = response.json()

# Parse the data into a DataFrame
df = pd.DataFrame({"timestamp": data["unix_seconds"], "price": data["price"]})
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
df["timestamp"] = df["timestamp"].dt.tz_convert("Europe/Brussels")
df.set_index("timestamp", inplace=True)
prices = df["price"]

# Create a line chart with Matplotlib
plt.figure(figsize=(10, 6))
plt.plot(prices.index, prices.values, label="Price")
plt.title("Day-Ahead Energy Prices")
plt.xlabel("Time")
plt.ylabel("Price (€/MWh)")
plt.legend()
plt.show()

print("Chart displayed in window.")
