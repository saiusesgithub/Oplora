from datetime import date
from typing import Any

from strands import tool

from agent.discovery.activity import run_state
from agent.models import EventMode, Opportunity


def _opportunity(**values: Any) -> dict:
    return Opportunity.model_validate(values).model_dump(mode="json", by_alias=True)


@tool
def discover_opportunities() -> list[dict]:
    """Discover the mocked opportunity catalog. Use this before evaluating matches."""
    opportunities = [
        _opportunity(id="hyd-ai-hack-2026", title="Hyderabad GenAI Builders Hackathon", organizer="T-Hub", description="A 36-hour build sprint for practical generative AI products.", location="T-Hub, Hyderabad", mode=EventMode.IN_PERSON, price=0, date=date(2026, 10, 10), registration_deadline=date(2026, 9, 28), tags=["hackathons", "AI", "startups", "developer events"], url="https://example.com/hyd-ai-hack-2026"),
        _opportunity(id="aws-user-group-oct", title="AWS User Group Hyderabad: Serverless Night", organizer="AWS User Group Hyderabad", description="Community talks and networking around serverless architecture and Bedrock.", location="Madhapur, Hyderabad", mode=EventMode.IN_PERSON, price=0, date=date(2026, 10, 3), registration_deadline=date(2026, 10, 2), tags=["AWS", "cloud", "developer events"], url="https://example.com/aws-user-group-oct"),
        _opportunity(id="bedrock-online-workshop", title="Build Agents with Amazon Bedrock Workshop", organizer="AWS Community Builders", description="An online guided workshop for AI agents using Amazon Bedrock.", location="Online", mode=EventMode.ONLINE, price=0, date=date(2026, 10, 15), registration_deadline=date(2026, 10, 14), tags=["AWS", "AI", "cloud", "workshops"], url="https://example.com/bedrock-online-workshop"),
        _opportunity(id="hyd-startup-weekend", title="Hyderabad Startup Weekend", organizer="Techstars Community", description="A weekend to validate ideas, form teams, and pitch startup concepts.", location="Banjara Hills, Hyderabad", mode=EventMode.IN_PERSON, price=499, date=date(2026, 10, 24), registration_deadline=date(2026, 10, 18), tags=["startups", "developer events", "competitions"], url="https://example.com/hyd-startup-weekend"),
        _opportunity(id="open-source-fellowship", title="Open Source AI Fellowship", organizer="MLH", description="Remote developer program pairing contributors with open-source AI projects.", location="Online", mode=EventMode.ONLINE, price=0, date=date(2026, 11, 2), registration_deadline=date(2026, 10, 12), tags=["AI", "developer programs", "cloud"], url="https://example.com/open-source-fellowship"),
        _opportunity(id="cloud-native-meetup", title="Cloud Native Hyderabad Meetup", organizer="CNCF Hyderabad", description="Local talks on Kubernetes, observability, and cloud engineering careers.", location="Gachibowli, Hyderabad", mode=EventMode.IN_PERSON, price=200, date=date(2026, 10, 8), registration_deadline=date(2026, 10, 7), tags=["cloud", "developer events"], url="https://example.com/cloud-native-meetup"),
        _opportunity(id="design-mumbai", title="Mumbai Product Design Conference", organizer="Design Forward", description="A full-day conference focused on UX research and visual design leadership.", location="Mumbai", mode=EventMode.IN_PERSON, price=3000, date=date(2026, 10, 20), registration_deadline=date(2026, 10, 5), tags=["design", "UX"], url="https://example.com/design-mumbai"),
        _opportunity(id="finance-cert", title="Advanced Financial Modelling Certification", organizer="Finance Academy", description="A paid online certification in corporate valuation and spreadsheet modelling.", location="Online", mode=EventMode.ONLINE, price=7999, date=date(2026, 11, 5), registration_deadline=date(2026, 10, 25), tags=["finance", "certification"], url="https://example.com/finance-cert"),
        _opportunity(id="chennai-robotics", title="Chennai Robotics League", organizer="RoboNation", description="An in-person competition for autonomous robotics teams.", location="Chennai", mode=EventMode.IN_PERSON, price=750, date=date(2026, 10, 30), registration_deadline=date(2026, 10, 10), tags=["robotics", "competitions"], url="https://example.com/chennai-robotics"),
    ]
    run_state.record("DISCOVERY_FOUND", f"Found {len(opportunities)} mock opportunities", discovered=len(opportunities))
    return opportunities
