# Oplora backend MVP

Oplora is an autonomous opportunity discovery agent for hackathons, developer events, workshops, competitions, internships, and developer programs.

The MVP uses FastAPI, Strands Agents, and Amazon Bedrock. Discovery data is deliberately mocked; selected opportunities are stored in process memory and disappear when the server restarts.

## Prerequisites

- Python 3.10+
- AWS credentials configured for an account with Amazon Bedrock model access
- Access to the configured model (defaults to `us.amazon.nova-pro-v1:0` in `us-east-1`)

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:AWS_REGION = "us-east-1"
# Optional: choose a Bedrock model available to your account
$env:BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"
uvicorn agent.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Endpoints

- `GET /health` — service status.
- `POST /agent/run` — asks Oplora to discover and save only strong matches.
- `GET /opportunities` — returns strong matches saved during this process lifetime.

## Example

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/agent/run
Invoke-RestMethod http://127.0.0.1:8000/opportunities
```

Oplora uses tools to retrieve the profile and opportunities, while the Bedrock model makes the relevance decision. It never submits applications; the approval tool only creates a structured pending approval request.
