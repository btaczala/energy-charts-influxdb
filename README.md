# Energy Charts InfluxDB Importer

This project fetches day-ahead energy prices from [energy-charts.info](https://energy-charts.info/) API, imports them into InfluxDB, and provides visualization tools. It includes Docker support for easy deployment.

## Features

- **Data Fetching**: Retrieve energy price data for any year and bidding zone
- **InfluxDB Integration**: Automatically import time-series data into InfluxDB
- **Visualization**: Plot energy prices using Matplotlib
- **Continuous Import**: Run importer in a loop for real-time updates
- **Docker Support**: Containerized setup with Docker Compose
- **Configuration**: Environment-based configuration for easy deployment

## Prerequisites

- Docker and Docker Compose
- InfluxDB instance (can be run via Docker or external)
- Git (for cloning)

## Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone git@github.com:btaczala/energy-charts-influxdb.git
   cd energy-charts-influxdb
   ```

2. **Configure environment variables** in `docker-compose.yml`:
   ```yaml
   environment:
     - YEAR=2023
     - BZN=DE-LU
     - INFLUX_URL=http://your-influxdb:8086
     - INFLUX_TOKEN=your-influxdb-token
     - INFLUX_ORG=your-influxdb-org
     - INFLUX_BUCKET=energy
   ```

3. **Run the importer**:
   ```bash
   docker-compose up --build
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f importer
   ```

The importer will fetch data for the specified year and continuously update every 15 minutes.

## Local Development

### Installation

1. **Install uv** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

### Usage

#### Plot Energy Prices

```bash
uv run python energy_prices_script.py --year 2023 --bzn DE-LU
```

This opens a Matplotlib window with the price chart for the year.

#### Import to InfluxDB

```bash
uv run python import_prices_to_influx.py --year 2023 --token your-token --org your-org --loop
```

Use `--loop` for continuous importing every 15 minutes.

#### Environment Variables

Set these for default values:

- `YEAR`: Year to process (default: 2023)
- `BZN`: Bidding zone (default: DE-LU)
- `INFLUX_URL`: InfluxDB URL (default: http://localhost:8086)
- `INFLUX_TOKEN`: InfluxDB token
- `INFLUX_ORG`: InfluxDB organization
- `INFLUX_BUCKET`: InfluxDB bucket (default: energy)

## API Reference

The project uses the energy-charts.info API:

- **Endpoint**: `https://api.energy-charts.info/price`
- **Parameters**:
  - `bzn`: Bidding zone (e.g., DE-LU, PL)
  - `start`: Start date (YYYY-MM-DD)
  - `end`: End date (YYYY-MM-DD)

## Docker Configuration

The `docker-compose.yml` includes:

- **Importer Service**: Runs the import script in a loop
- **Inline Dockerfile**: Builds the Python application with uv
- **Environment Variables**: Configurable via env vars

## Data Model

InfluxDB measurement: `energy_prices`

Tags:
- `bzn`: Bidding zone

Fields:
- `price`: Price value (EUR/MWh)

Time: Unix timestamp

## Troubleshooting

- **No output in Docker**: Check `docker-compose logs importer`
- **InfluxDB connection errors**: Verify URL, token, and org
- **API errors**: Check bidding zone and date range validity
- **Permission denied**: Ensure SSH key is set up for GitHub

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details