# USSD Voting App (FastAPI + SQLite)

Backend for a USSD-based voting flow with mock MTN MoMo payment. Users must pay before their vote is recorded. Results are available via an admin endpoint.

## Stack
- FastAPI
- SQLite (SQLAlchemy)
- Pluggable payment provider (mock included)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r /workspace/requirements.txt
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Health check: `GET /healthz`
- USSD: `POST /ussd` (content-type: `application/x-www-form-urlencoded` or JSON)
- Admin results JSON: `GET /admin/results`
- Admin HTML dashboard: `GET /admin`

## USSD Payload Examples

Form or JSON keys typical of gateways:
- `sessionId`: unique session identifier
- `phoneNumber`: MSISDN (e.g., 2567XXXXXXX)
- `text`: cumulative user input (e.g., `1*1`); last token is used per step

Example using JSON:

```bash
curl -s -X POST http://localhost:8000/ussd \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"abc123","phoneNumber":"256700000001","text":""}'
```

Follow-up step (select candidate A and confirm):

```bash
# Step 1: show menu
curl -s -X POST http://localhost:8000/ussd \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"abc123","phoneNumber":"256700000001","text":""}'

# Step 2: choose 1 (A)
curl -s -X POST http://localhost:8000/ussd \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"abc123","phoneNumber":"256700000001","text":"1"}'

# Step 3: confirm payment (1)
curl -s -X POST http://localhost:8000/ussd \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"abc123","phoneNumber":"256700000001","text":"1*1"}'
```

The mock provider confirms immediately and records the vote. Duplicate votes by the same phone are prevented.

## Swapping to Real MTN MoMo Later
- Implement a new provider class extending `app/payment/base.py:PaymentProvider`
- Wire it in `app/routers/ussd.py` where the mock is used
- Optionally add a payment callback endpoint to update `Payment` status and record the vote on confirmation
