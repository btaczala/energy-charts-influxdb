import argparse
import logging
import os
import pandas as pd
import requests
import time
from influxdb_client import InfluxDBClient, Point

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting energy prices importer...")
parser = argparse.ArgumentParser(
    description="Import energy prices for a year into InfluxDB")
parser.add_argument("--year",
                    type=int,
                    default=int(os.getenv("YEAR", "2026")),
                    help="Year to import")
parser.add_argument("--bzn",
                    type=str,
                    default=os.getenv("BZN", "DE-LU"),
                    help="Bidding zone")
parser.add_argument(
    "--url",
    type=str,
    default=os.getenv("INFLUX_URL", "http://localhost:8086"),
    help="InfluxDB URL",
)
parser.add_argument("--token",
                    type=str,
                    default=os.getenv("INFLUX_TOKEN", ""),
                    help="InfluxDB token")
parser.add_argument("--org",
                    type=str,
                    default=os.getenv("INFLUX_ORG", ""),
                    help="InfluxDB org")
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

logger.info(f"Configuration - Year: {args.year}, BZN: {args.bzn}")
logger.info(f"InfluxDB - URL: {args.url}, Org: {args.org}, Bucket: {args.bucket}")

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

    logger.info(f"Fetching data for {year}, bidding zone {bzn}...")
    logger.info(f"Date range: {start_date} to {end_date}")

    # Fetch day-ahead prices from energy-charts.info API
    url = "https://api.energy-charts.info/price"
    params = {"bzn": bzn, "start": start_date, "end": end_date}
    logger.debug(f"Making request to: {url}")
    logger.debug(f"Request params: {params}")
    response = requests.get(url, params=params)
    logger.info(f"Response status code: {response.status_code}")

    if response.status_code != 200:
        logger.error(f"API request failed with status {response.status_code}")
        logger.error(f"Response content: {response.text}")
        time.sleep(60)  # Wait before retrying
        continue

    data = response.json()
    logger.info(
        f"Received data with {len(data.get('unix_seconds', []))} data points")
    logger.debug(f"Data keys: {list(data.keys())}")

    # Parse timestamps
    logger.info("Parsing timestamps and prices...")
    timestamps = [pd.to_datetime(ts, unit="s") for ts in data["unix_seconds"]]
    prices = data["price"]

    # Show sample data
    logger.debug(f"Sample timestamp: {timestamps[0] if timestamps else 'None'}")
    logger.debug(f"Sample price: {prices[0] if prices else 'None'}")
    logger.info(
        f"Price range: {min(prices) if prices else 'N/A'} to {max(prices) if prices else 'N/A'}"
    )

    # Connect to InfluxDB
    logger.info("Connecting to InfluxDB...")
    client = InfluxDBClient(url=args.url, token=args.token, org=args.org)
    write_api = client.write_api()
    logger.info("Successfully connected to InfluxDB")

    # Check if bucket exists, create if it doesn't
    logger.info(f"Checking for bucket '{args.bucket}'...")
    buckets_api = client.buckets_api()
    try:
        bucket = buckets_api.find_bucket_by_name(args.bucket)
        if bucket is None:
            logger.warning(f"Bucket '{args.bucket}' not found. Creating it...")
            buckets_api.create_bucket(bucket_name=args.bucket, org=args.org)
            logger.info(f"Bucket '{args.bucket}' created successfully.")
        else:
            logger.info(f"Bucket '{args.bucket}' already exists.")
            logger.debug(f"Bucket ID: {bucket.id}")
    except Exception as e:
        logger.error(f"Error managing bucket: {e}")
        client.close()
        raise

    # Create points
    logger.info(f"Creating {len(timestamps)} data points...")
    points = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        point = Point("energy_prices").tag("bzn", bzn).field("price",
                                                             price).time(ts)
        points.append(point)
        if i < 3:  # Show first 3 points as examples
            logger.debug(f"  Point {i+1}: timestamp={ts}, price={price}")
            logger.debug(
                f"    Measurement: energy_prices, Tag: bzn={bzn}, Field: price={price}"
            )

    logger.info(
        f"Writing {len(points)} points to InfluxDB bucket '{args.bucket}'...")
    logger.debug(
        f"Write details - Measurement: 'energy_prices', Tag: 'bzn'='{bzn}', Field: 'price'"
    )

    # Write to InfluxDB
    try:
        write_api.write(bucket=args.bucket, record=points)
        logger.info(
            f"Successfully imported {len(points)} price points for {year} into InfluxDB."
        )
        logger.info(f"Data written to bucket: '{args.bucket}'")
        logger.info(f"Organization: '{args.org}'")
        logger.info(f"Measurement: 'energy_prices'")
        logger.info(f"Tag filter: bzn='{bzn}'")
    except Exception as e:
        logger.error(f"Error writing to InfluxDB: {e}")
        logger.error(f"Bucket: '{args.bucket}'")
        logger.error(f"Org: '{args.org}'")
        logger.error(f"Points attempted: {len(points)}")
        client.close()
        raise

    # Verify data was written
    logger.info("Verifying data was written correctly...")
    query_api = client.query_api()

    # First check total count
    logger.info("Running count query...")
    count_query = f'''
    from(bucket: "{args.bucket}")
      |> range(start: 0)
      |> filter(fn: (r) => r._measurement == "energy_prices")
      |> filter(fn: (r) => r.bzn == "{bzn}")
      |> count()
    '''

    try:
        result = query_api.query(count_query)
        logger.debug(f"Count query executed. Tables returned: {len(result)}")
        for table in result:
            for record in table.records:
                logger.info(f"Total records in bucket: {record.get_value()}")

        # Now check for recent data with timestamps - exact match to Data Explorer format
        logger.info("Running Data Explorer style query...")
        data_explorer_query = f'''
        from(bucket: "{args.bucket}")
          |> range(start: -24h, stop: now())
          |> filter(fn: (r) => r["_measurement"] == "energy_prices")
          |> filter(fn: (r) => r["bzn"] == "{bzn}")
          |> filter(fn: (r) => r["_field"] == "price")
          |> limit(n: 5)
        '''

        result = query_api.query(data_explorer_query)
        logger.debug(
            f"Data Explorer style query executed. Tables returned: {len(result)}"
        )

        if len(result) == 0:
            logger.warning("No data found with exact Data Explorer format!")
            logger.info("Checking what's actually in the bucket...")

            # Check for any data in the last 24 hours
            any_data_query = f'''
            from(bucket: "{args.bucket}")
              |> range(start: -24h, stop: now())
              |> limit(n: 10)
            '''

            result = query_api.query(any_data_query)
            if len(result) == 0:
                logger.warning("No data at all in the bucket in last 24h")
            else:
                logger.info("Sample raw data found:")
                for table in result:
                    for record in table.records:
                        logger.debug(f"Measurement: {record.get_measurement()}")
                        logger.debug(f"Field: {record.get_field()}")
                        logger.debug(f"Value: {record.get_value()}")
                        logger.debug(f"Tags: {record.values}")
                        logger.debug(f"Time: {record.get_time()}")
                        logger.debug("---")

            logger.info("Exact Data Explorer query to use:")
            logger.info(f"from(bucket: \"{args.bucket}\")")
            logger.info(
                "|> range(start: v.timeRangeStart, stop: v.timeRangeStop)"
            )
            logger.info(
                "|> filter(fn: (r) => r[\"_measurement\"] == \"energy_prices\")"
            )
            logger.info(f"|> filter(fn: (r) => r[\"bzn\"] == \"{bzn}\")")
            logger.info("|> filter(fn: (r) => r[\"_field\"] == \"price\")")
            logger.info(
                "|> aggregateWindow(every: 10s, fn: mean, createEmpty: false)"
            )
            logger.info("|> yield(name: \"mean\")")
        else:
            logger.info("Data found with exact format:")
            for table in result:
                for record in table.records:
                    logger.info(
                        f"Time: {record.get_time()}, Field: {record.get_field()}, Value: {record.get_value()}"
                    )
                    logger.debug(f"Tags: {record.values}")

        # Check all measurements in bucket (broader time range)
        logger.info("Checking all measurements in bucket...")
        measurements_query = f'''
        from(bucket: "{args.bucket}")
          |> range(start: -7d)
          |> group(columns: ["_measurement"])
          |> distinct(column: "_measurement")
        '''

        result = query_api.query(measurements_query)
        measurements = []
        for table in result:
            for record in table.records:
                measurements.append(record.values.get("_measurement"))

        logger.info(f"Measurements in bucket: {measurements}")

        # Check all tags for energy_prices measurement
        if "energy_prices" in measurements:
            logger.info("Checking tags for energy_prices measurement...")
            tags_query = f'''
            from(bucket: "{args.bucket}")
              |> range(start: -7d)
              |> filter(fn: (r) => r._measurement == "energy_prices")
              |> group(columns: ["bzn"])
              |> distinct(column: "bzn")
            '''

            result = query_api.query(tags_query)
            tags = []
            for table in result:
                for record in table.records:
                    tags.append(record.values.get("bzn"))

            logger.info(f"BZN tags found: {tags}")

            # Check for specific field names
            logger.info("Checking field names for energy_prices measurement...")
            fields_query = f'''
            from(bucket: "{args.bucket}")
              |> range(start: -7d)
              |> filter(fn: (r) => r._measurement == "energy_prices")
              |> group(columns: ["_field"])
              |> distinct(column: "_field")
            '''

            result = query_api.query(fields_query)
            fields = []
            for table in result:
                for record in table.records:
                    fields.append(record.values.get("_field"))

            logger.info(f"Field names found: {fields}")
        else:
            logger.warning("'energy_prices' measurement not found!")

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        logger.error(f"Query attempted on bucket: '{args.bucket}'")
        logger.error(f"In organization: '{args.org}'")

    # Close APIs
    write_api.close()
    client.close()
    logger.info("InfluxDB connection closed.")

    if not args.loop:
        break
    logger.info("Sleeping for 15 minutes...")
    time.sleep(15 * 60)
