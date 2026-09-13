from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool

from agent.agent import create_oplora_agent
from agent.models import AgentRunResponse, SavedOpportunity
from agent.tools.applications import saved_opportunities

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.oplora = create_oplora_agent()
    logger.info("Oplora agent initialized")
    yield


app = FastAPI(title="Oplora Backend MVP", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/opportunities", response_model=list[SavedOpportunity])
def get_opportunities() -> list[SavedOpportunity]:
    return saved_opportunities()


@app.post("/agent/run", response_model=AgentRunResponse)
async def run_agent() -> AgentRunResponse:
    prompt = "Discover the best current opportunities for me and save only strong matches."
    logger.info("Starting Oplora discovery run")
    try:
        result = await run_in_threadpool(app.state.oplora, prompt)
    except Exception as exc:
        logger.exception("Oplora discovery run failed")
        raise HTTPException(status_code=502, detail="Oplora could not reach its Bedrock model.") from exc
    return AgentRunResponse(response=str(result), saved_opportunities=saved_opportunities())
