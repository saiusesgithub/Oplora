from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)

from fastapi import FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool

from agent.agent import create_oplora_agent, model_provider_name
from agent.discovery.activity import run_state
from agent.discovery.web_search import get_search_provider, search_provider_name
from agent.models import AgentRunRequest, AgentRunResponse, SavedOpportunity
from agent.tools.applications import clear_evaluated_opportunities, saved_opportunities

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _is_nova_tool_use_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "modelstreamerrorexception" in message
        or "invalid sequence as part of tooluse" in message
        or "malformed tooluse" in message
    )


def _partial_result_detail() -> dict:
    stats = run_state.snapshot()
    return {
        "message": "Oplora's model failed after one retry; real partial results were preserved.",
        "discovered": stats["discovered"],
        "deduplicated": stats["deduplicated"],
        "evaluated": stats["evaluated"],
        "saved": stats["saved"],
        "saved_opportunities": [item.model_dump(mode="json") for item in saved_opportunities()],
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Model provider: %s", model_provider_name())
    logger.info("Search provider: %s", search_provider_name())
    app.state.oplora = create_oplora_agent()
    yield


app = FastAPI(title="Oplora Backend MVP", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/opportunities", response_model=list[SavedOpportunity])
def get_opportunities() -> list[SavedOpportunity]:
    return saved_opportunities()


@app.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest | None = None) -> AgentRunResponse:
    configured_mode = os.getenv("OPLORA_DISCOVERY_MODE", "mock").lower()
    mode = request.mode if request else configured_mode
    if mode not in {"mock", "web"}:
        raise HTTPException(status_code=422, detail="Discovery mode must be 'mock' or 'web'.")
    if mode == "web" and get_search_provider() is None:
        raise HTTPException(
            status_code=503,
            detail="Web discovery is not configured. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY.",
        )
    prompt = f"Discover the best current opportunities for me and save only strong matches. Use {mode} discovery mode."
    run_state.reset()
    clear_evaluated_opportunities()
    logger.info("Starting Oplora %s discovery run", mode)
    try:
        result = await run_in_threadpool(app.state.oplora, prompt)
    except Exception as exc:
        if model_provider_name() == "Bedrock" and _is_nova_tool_use_error(exc):
            run_state.record("MODEL_RETRY", "Retrying after a Nova tool-use response error")
            try:
                result = await run_in_threadpool(
                    app.state.oplora,
                    "Continue the current discovery operation from prior tool results. Do not restart searches or use mock data.",
                )
            except Exception as retry_exc:
                logger.warning("Oplora Nova tool-use retry failed")
                raise HTTPException(status_code=502, detail=_partial_result_detail()) from retry_exc
        else:
            logger.warning("Oplora discovery run failed")
            raise HTTPException(status_code=502, detail="Oplora could not complete its model run.") from exc
    stats = run_state.snapshot()
    return AgentRunResponse(
        response=str(result),
        discovered=stats["discovered"],
        deduplicated=stats["deduplicated"],
        evaluated=stats["evaluated"],
        saved=stats["saved"],
        saved_opportunities=saved_opportunities(),
    )
