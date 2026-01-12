# API Usage Examples & Cookbook

## Quick Start
- Base URL: `http://localhost:8000`
- Authentication: none
- Common headers:
  - `Content-Type: application/json`
  - `Accept: application/json`

## Common Usage Scenarios
### Scenario 1: Run a strategy analysis for one symbol
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  symbol="AAPL" \
  strategy="RSI2" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Scenario 2: Run the basic screener with default watchlist
**curl**
```bash
curl -X POST "http://localhost:8000/screener/basic" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "market_type": "stock",
    "lookback_days": 200,
    "min_score": 30
  }'
```

**httpie**
```bash
http POST http://localhost:8000/screener/basic \
  Content-Type:application/json \
  Accept:application/json \
  market_type="stock" \
  lookback_days:=200 \
  min_score:=30
```

**Postman (raw)**
```
POST http://localhost:8000/screener/basic
Content-Type: application/json
Accept: application/json

{
  "market_type": "stock",
  "lookback_days": 200,
  "min_score": 30
}
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Scenario 3: Read recent signals with filters
**curl**
```bash
curl -X GET "http://localhost:8000/signals?symbol=AAPL&strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

**httpie**
```bash
http GET http://localhost:8000/signals \
  symbol=="AAPL" \
  strategy=="RSI2" \
  limit==10 \
  Accept:application/json
```

**Postman (raw)**
```
GET http://localhost:8000/signals?symbol=AAPL&strategy=RSI2&limit=10
Accept: application/json
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

## Error Examples
### Error 1: 400 Invalid strategy
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "symbol": "AAPL",
    "strategy": "UNKNOWN",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  symbol="AAPL" \
  strategy="UNKNOWN" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "symbol": "AAPL",
  "strategy": "UNKNOWN",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `400 Bad Request`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Error 2: 404 Not found (unknown route)
**curl**
```bash
curl -X GET "http://localhost:8000/unknown/resource" \
  -H "Accept: application/json"
```

**httpie**
```bash
http GET http://localhost:8000/unknown/resource \
  Accept:application/json
```

**Postman (raw)**
```
GET http://localhost:8000/unknown/resource
Accept: application/json
```

**Expected status:** `404 Not Found`

**Sample response**
```json
{
  "detail": "Not Found"
}
```

### Error 3: 422 Missing required field
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  strategy="RSI2" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `422 Unprocessable Entity`

**Sample response**
```json
{
  "detail": [
    {
      "loc": ["body", "symbol"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```
