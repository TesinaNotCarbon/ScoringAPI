# Mock Score API

Simple mock API to test Chainlink Functions or other oracle systems.

This API is now implemented in Python using FastAPI.

## Requirements

- Python 3.10+

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API:

```bash
python main.py
```

The API listens on `PORT` if defined, otherwise on `3000`.

## Endpoints

### GET /

Health check endpoint.

Response (plain text):

```text
Mock Score API is running
```

### GET /score

Returns a deterministic score.

Response:

```json
{ "score": 87 }
```

### GET /score-unstable

Returns a score by default, but can simulate a failure.

- `GET /score-unstable`

```json
{ "score": 87 }
```

- `GET /score-unstable?fail=true`

Status: `500`

```json
{ "error": "Simulated failure" }
```

## Notes

- The HTTP API runtime is now FastAPI.
