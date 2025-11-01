# Phone Number Lookup API

A FastAPI service for phone number validation with country origin information.

## Features

- Phone number validation and formatting
- Country detection and information lookup
- X-API-TOKEN authentication
- Support for 249+ countries
- Interactive API documentation at `/docs`

## Quick Start

### Using Docker Compose (Recommended)

```bash
API_TOKEN="your-secure-token" docker-compose up -d
```

### Using Docker

```bash
docker build -t phone-api .
docker run -d -p 8000:8000 -e API_TOKEN="your-token" phone-api
```

### Local Installation

```bash
pip install -r requirements.txt
python main.py
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Lookup Phone Number
```bash
GET /lookup?phone=14155552671&country=US
```
Requires `X-API-TOKEN` header.

### Validate Phone Number
```bash
GET /validate?phone=+14155552671
```
Requires `X-API-TOKEN` header.

### Get Supported Countries
```bash
GET /supported-countries
```
Requires `X-API-TOKEN` header.

## Usage Example

```bash
curl -H "X-API-TOKEN: your-token" \
  "http://localhost:8000/lookup?phone=14155552671"
```

## Environment Variables

- `API_TOKEN` - Authentication token (default: dev-token)
- `PORT` - Server port (default: 8000)
- `HOST` - Bind address (default: 0.0.0.0)
- `WORKERS` - Worker processes (default: 4)

## Response Format

```json
{
  "phone_number": "+1 415-555-2671",
  "country_code": "US",
  "country_name": "United States",
  "number_type": "MOBILE",
  "is_valid": true,
  "is_possible": true,
  "formatted_e164": "+14155552671",
  "formatted_national": "(415) 555-2671"
}
```

## Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- phonenumbers - Phone number validation
- pycountry - Country information
- Pydantic - Data validation
