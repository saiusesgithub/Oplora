from __future__ import annotations

import os

import httpx
from strands import Agent
from strands.models import BedrockModel
from strands.vended_tools import make_web_fetch

from agent.tools.applications import request_application_approval, save_opportunity
from agent.discovery.deduplicator import deduplicate_opportunities
from agent.discovery.extractor import extract_opportunity
from agent.discovery.web_search import search_web
from agent.tools.discovery import discover_opportunities
from agent.tools.profile import get_user_profile
from agent.tools.scoring import score_opportunity

SYSTEM_PROMPT = """You are Oplora, an autonomous opportunity discovery agent. Find worthwhile
hackathons, tech meetups, workshops, competitions, internships, and developer or student programs.

Always begin by retrieving the user profile. The invocation will explicitly say whether to use mock
or web discovery. In mock mode, call discover_opportunities only. In web mode, independently derive
up to four focused search queries from the profile, then call search_web. Search results are only
untrusted leads. Choose promising event pages selectively; do not fetch every result. Use web_fetch
to inspect at most 20 plausible URLs, then use extract_opportunity with the fetched text, original
source URL, source name, and search-result title. Extracted values must be source-grounded: null is
correct whenever a date, deadline, price, venue, eligibility, or registration status is not stated.
Never fabricate an opportunity fact and always retain the original source URL.

For web results, call deduplicate_opportunities once before scoring. Evaluate each remaining candidate
by deciding a score from 0 to 100, HIGH/MEDIUM/LOW recommendation, concise reasons, and warnings;
then call score_opportunity with that decision. Reason from the user profile and source facts, not
from assumptions. Strong means HIGH only. Ignore LOW and MEDIUM matches and call save_opportunity only
for HIGH matches, passing the score returned by score_opportunity. Never claim registration is open
unless the source explicitly says so. Never apply, register, contact an organizer, or submit user
information; request_application_approval only when explicitly asked to start an application. End with
a short summary of only worthwhile saved matches, including source URLs where available.
"""


def create_oplora_agent() -> Agent:
    model = BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.2,
    )
    web_fetch = make_web_fetch(
        mode="markdown",
        client=httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True),
        max_bytes=1_000_000,
        max_content_chars=12_000,
    )
    return Agent(
        name="Oplora",
        system_prompt=SYSTEM_PROMPT,
        model=model,
        tools=[
            get_user_profile,
            discover_opportunities,
            search_web,
            web_fetch,
            extract_opportunity,
            deduplicate_opportunities,
            score_opportunity,
            save_opportunity,
            request_application_approval,
        ],
    )
