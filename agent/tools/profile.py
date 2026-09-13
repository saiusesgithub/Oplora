from strands import tool

from agent.models import UserProfile


@tool
def get_user_profile() -> dict:
    """Return the current demo user's opportunity preferences."""
    profile = UserProfile(
        city="Hyderabad",
        radius_km=30,
        max_price_inr=500,
        interests=["hackathons", "AI", "AWS", "cloud", "developer events", "startups"],
        online_events_allowed=True,
    )
    return profile.model_dump()
