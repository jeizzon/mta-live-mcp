# MTA Live Data MCP Server

A remote MCP (Model Context Protocol) server that provides real-time NYC transit data for AI tools. Query subway arrivals, bus schedules, LIRR and Metro-North trains, service alerts, and more.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and designed for deployment on Railway.

## Features

- **Real-time arrivals** for NYC Subway, MTA Buses, LIRR, and Metro-North
- **Location-based search** - find nearby stations by latitude/longitude
- **Station search** - find stations by name
- **Service alerts** - get active delays and service changes
- **Line status** - check if a specific subway line has delays
- **Simple token auth** - secure your server with a bearer token

## Available MCP Tools

### Subway (NYC Subway)
| Tool | Description |
|------|-------------|
| `get_subway_arrivals(stop_id)` | Get upcoming arrivals at a specific subway stop |
| `get_nearby_subway_arrivals(lat, lon, radius_meters)` | Find nearby stations and get their arrivals |
| `get_subway_alerts()` | Get active service alerts for NYC Subway |
| `get_subway_line_status(line)` | Get delay info for a line (e.g., "A", "L", "7") |
| `search_subway_stations(query)` | Search stations by name |
| `find_nearby_subway_stations(lat, lon, radius_meters)` | Find nearby subway stations |

### Bus (MTA Buses)
| Tool | Description |
|------|-------------|
| `get_bus_arrivals(stop_id)` | Get upcoming arrivals at a bus stop |
| `get_nearby_bus_arrivals(lat, lon)` | Find nearby bus stops and get arrivals |
| `get_bus_alerts()` | Get active service alerts for MTA buses |

> **Note:** Bus tools require the `MTA_BUS_API_KEY` environment variable. Get a free API key at [register.developer.obanyc.com](https://register.developer.obanyc.com/).

### LIRR (Long Island Rail Road)
| Tool | Description |
|------|-------------|
| `get_lirr_arrivals(stop_id)` | Get upcoming LIRR arrivals at a station |
| `get_nearby_lirr_arrivals(lat, lon, radius_meters)` | Find nearby LIRR stations and get arrivals |
| `get_lirr_alerts()` | Get active service alerts for LIRR |
| `search_lirr_stations(query)` | Search LIRR stations by name |
| `find_nearby_lirr_stations(lat, lon, radius_meters)` | Find nearby LIRR stations |

### Metro-North
| Tool | Description |
|------|-------------|
| `get_metro_north_arrivals(stop_id)` | Get upcoming Metro-North arrivals |
| `get_nearby_metro_north_arrivals(lat, lon, radius_meters)` | Find nearby Metro-North stations and get arrivals |
| `get_metro_north_alerts()` | Get active service alerts for Metro-North |
| `search_metro_north_stations(query)` | Search Metro-North stations by name |
| `find_nearby_metro_north_stations(lat, lon, radius_meters)` | Find nearby Metro-North stations |

### Server
| Tool | Description |
|------|-------------|
| `get_server_info()` | Get server status and configuration info |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MCP_AUTH_TOKEN` | **Yes** | Bearer token for authenticating requests |
| `MTA_BUS_API_KEY` | No | MTA Bus Time API key (bus tools won't work without it) |
| `PORT` | No | Server port (default: 8000) |

## Local Development

### Setup

```bash
git clone https://github.com/yourusername/mta-live-mcp.git
cd mta-live-mcp

# Create virtual environment (conda or venv)
conda create -n mta-mcp python=3.13
conda activate mta-mcp

# Or with venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment

```bash
# Required: Set your auth token
export MCP_AUTH_TOKEN="your-secret-token-here"

# Optional: Set bus API key
export MTA_BUS_API_KEY="your-bus-api-key"
```

### Run the Server

```bash
python src/server.py
```

The server will:
1. Load station data from MTA (subway, LIRR, Metro-North)
2. Start listening on `http://0.0.0.0:8000`

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Open http://localhost:3000 and connect to `http://localhost:8000/mcp` using "Streamable HTTP" transport.

**Important:** Include your auth token in the headers:
```
Authorization: Bearer your-secret-token-here
```

## Deployment on Railway

### 1. Create a Railway Project

1. Go to [railway.app](https://railway.app)
2. Create a new project from GitHub repo
3. Select your forked repository

### 2. Configure Environment Variables

In Railway dashboard, add these environment variables:

- `MCP_AUTH_TOKEN` - Your secret authentication token
- `MTA_BUS_API_KEY` - (Optional) Your MTA Bus API key

### 3. Deploy

Railway will automatically detect `railway.json` and deploy your server.

Your server will be available at:
```
https://your-project-name.up.railway.app/mcp
```

## HTTP Endpoints

### MCP Endpoint
- **URL:** `/mcp`
- **Auth:** Bearer token required
- **Description:** Main MCP protocol endpoint for AI tools

### Health Check
- **URL:** `/health`
- **Method:** GET
- **Auth:** None required
- **Description:** Returns server health status

### Refresh Station Data
- **URL:** `/refresh`
- **Method:** POST
- **Auth:** Bearer token required
- **Description:** Reload station data from MTA sources

Example:
```bash
curl -X POST https://your-server.railway.app/refresh \
  -H "Authorization: Bearer your-token"
```

## Authentication

All MCP tool calls require authentication via Bearer token:

```
Authorization: Bearer your-secret-token
```

The token is validated against the `MCP_AUTH_TOKEN` environment variable. Requests without a valid token receive a 401 Unauthorized response.

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Data Sources

This server uses official MTA data feeds:

- **Subway:** [MTA GTFS-RT feeds](https://api.mta.info/) (no API key required)
- **LIRR/Metro-North:** [MTA GTFS-RT feeds](https://api.mta.info/) (no API key required)
- **Buses:** [MTA Bus Time SIRI API](https://bustime.mta.info/wiki/Developers/Index) (free API key required)
- **Service Alerts:** [MTA GTFS-RT alerts](https://api.mta.info/) (no API key required)
- **Station Data:** [MTA Static GTFS](https://www.mta.info/developers) (downloaded on startup)

## Example Queries

Once connected to an AI tool, you can ask questions like:

- "What are the next trains arriving at 14th Street Union Square?"
- "Are there any delays on the A train?"
- "Find subway stations near Times Square"
- "When is the next LIRR train from Penn Station?"
- "Are there any service alerts for the L train?"
- "Find bus stops near 40.7128, -74.0060"

## Project Structure

```
mta-live-mcp/
├── src/
│   ├── server.py        # Main MCP server with all tools
│   ├── auth.py          # Authentication middleware
│   ├── station_data.py  # Station loading and geo-lookup
│   └── mta_feeds.py     # GTFS-RT and SIRI API parsing
├── tests/
│   ├── conftest.py      # Test fixtures
│   ├── test_station_data.py
│   ├── test_mta_feeds.py
│   └── test_server.py
├── requirements.txt
├── railway.json         # Railway deployment config
└── README.md
```

## License

MIT
