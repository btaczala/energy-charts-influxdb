import argparse
import os
import pandas as pd
import requests
import time
from influxdb_client import InfluxDBClient, Point

print("Starting energy prices importer...")
parser = argparse.ArgumentParser(
    description="Import energy prices for a year into InfluxDB"
)
parser.add_argument(
    "--year", type=int, default=int(os.getenv("YEAR", "2023")), help="Year to import"
)
parser.add_argument(
    "--bzn", type=str, default=os.getenv("BZN", "DE-LU"), help="Bidding zone"
)
parser.add_argument(
    "--url",
    type=str,
    default=os.getenv("INFLUX_URL", "http://localhost:8086"),
    help="InfluxDB URL",
)
parser.add_argument(
    "--token", type=str, default=os.getenv("INFLUX_TOKEN", ""), help="InfluxDB token"
)
parser.add_argument(
    "--org", type=str, default=os.getenv("INFLUX_ORG", ""), help="InfluxDB org"
)
parser.add_argument(
    "--bucket",
    type=str,
    default=os.getenv("INFLUX_BUCKET", "energy"),
    help="InfluxDB bucket",
)
parser.add_argument(
    "--loop",
    action="store_true",
    help="Run in loop every 15 minutes",
)
args = parser.parse_args()

if not args.token:
    parser.error(
        "InfluxDB token is required (set INFLUX_TOKEN environment variable or --token)"
    )
if not args.org:
    parser.error(
        "InfluxDB org is required (set INFLUX_ORG environment variable or --org)"
    )

while True:
    year = args.year
    bzn = args.bzn
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # Fetch day-ahead prices from energy-charts.info API
    url = "https://api.energy-charts.info/price"
    params = {"bzn": bzn, "start": start_date, "end": end_date}
    response = requests.get(url, params=params)
    data = response.json()

    # Parse timestamps
    timestamps = [pd.to_datetime(ts, unit="s") for ts in data["unix_seconds"]]
    prices = data["price"]

    # Connect to InfluxDB
    client = InfluxDBClient(url=args.url, token=args.token, org=args.org)
    write_api = client.write_api()

    # Create points
    points = []
    for ts, price in zip(timestamps, prices):
        point = Point("energy_prices").tag("bzn", bzn).field("price", price).time(ts)
        points.append(point)

    # Write to InfluxDB
    write_api.write(bucket=args.bucket, record=points)

    print(f"Imported {len(points)} price points for {year} into InfluxDB.")

    # Close APIs
    write_api.close()
    client.close()

    if not args.loop:
        break
    print("Sleeping for 15 minutes...")
    time.sleep(15 * 60)
