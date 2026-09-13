# Oplora backend MVP

Oplora is an autonomous opportunity discovery agent for hackathons, developer events, workshops, competitions, internships, and developer programs.

The MVP uses FastAPI, Strands Agents, Amazon Bedrock, and bounded web discovery. Mock discovery remains available for reliable demos. Selected opportunities and activity are stored in process memory and disappear when the server restarts.

## Prerequisites

- Python 3.10+
- AWS credentials configured for an account with Amazon Bedrock model access
- Access to the configured model (defaults to `us.amazon.nova-pro-v1:0` in `us-east-1`)
- For web mode, one configured search provider: Tavily or Brave Search

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:AWS_REGION = "us-east-1"
# Optional: choose a Bedrock model available to your account
$env:BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"
# Optional web-search provider; Tavily takes precedence if both are set.
$env:TAVILY_API_KEY = "..."
# $env:BRAVE_SEARCH_API_KEY = "..."
uvicorn agent.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Endpoints

- `GET /health` — service status.
- `POST /agent/run` — asks Oplora to discover and save only strong matches. Its optional body accepts `{"mode":"mock"}` (default) or `{"mode":"web"}`.
- `GET /opportunities` — returns strong matches saved during this process lifetime.

## Example

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/agent/run
Invoke-RestMethod -Method Post http://127.0.0.1:8000/agent/run -ContentType "application/json" -Body '{"mode":"web"}'
Invoke-RestMethod http://127.0.0.1:8000/opportunities
```

In web mode, Oplora independently chooses focused searches from the profile, receives a bounded number of result pages, selectively reads likely event pages using Strands Web Fetch, extracts only source-supported details, removes deterministic duplicates, and asks Bedrock to evaluate the remaining opportunities. A run response includes discovered, deduplicated, evaluated, and saved counts. Real opportunities retain `source`, `source_url`, and `discovered_at`; missing source details are `null`, not guesses.

Set `OPLORA_DISCOVERY_MODE=mock` or `OPLORA_DISCOVERY_MODE=web` as your deployment default if desired. The request body mode always takes precedence. A configured search API key is still required for web discovery. Oplora never submits applications; the approval tool only creates a structured pending approval request.
