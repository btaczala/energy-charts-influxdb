# Energy Charts InfluxDB Importer

This project fetches day-ahead energy prices from [energy-charts.info](https://energy-charts.info/) API, imports them into InfluxDB.

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

## License

Apache License - see [LICENSE](LICENSE) file for details
