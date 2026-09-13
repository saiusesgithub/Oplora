from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from agent.tools.applications import request_application_approval, save_opportunity
from agent.tools.discovery import discover_opportunities
from agent.tools.profile import get_user_profile
from agent.tools.scoring import score_opportunity

SYSTEM_PROMPT = """You are Oplora, an autonomous opportunity discovery agent.
Find worthwhile hackathons, tech meetups, workshops, competitions, internships, and developer programs.

For each run, first call get_user_profile, then discover_opportunities. Evaluate every candidate
using score_opportunity and reason from the profile and opportunity facts. For every evaluation,
state a score from 0 to 100, recommendation (HIGH, MEDIUM, or LOW), concise reasons, and warnings.
Strong means HIGH only. Ignore LOW and MEDIUM matches; call save_opportunity only for HIGH matches.
Never invent opportunities or facts. Never apply, register, contact an organizer, or submit user
information: request_application_approval only when explicitly asked to start an application.
Surface only saved strong matches in a short, useful summary.
"""


def create_oplora_agent() -> Agent:
    model = BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.2,
    )
    return Agent(
        name="Oplora",
        system_prompt=SYSTEM_PROMPT,
        model=model,
        tools=[get_user_profile, discover_opportunities, score_opportunity, save_opportunity, request_application_approval],
    )
