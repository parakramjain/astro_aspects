from __future__ import annotations

from career_intent.app.schemas.input import CareerInsightRequest


def _base_payload() -> dict:
    return {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6},
    }


def test_user_profile_optional_and_cleaned():
    payload = _base_payload()
    payload["user_profile"] = {
        "current_role_title": "  Senior Data Scientist  ",
        "experience_years": 10,
        "target_roles": ["GenAI Architect", "GenAI Architect", "  ", "ML Lead", "Director", "Extra"],
        "strengths_top3": ["Python", "Python", "ML", "Stakeholder management", "extra"],
        "gaps_top3": ["LLMOps", "System design", "Product thinking", "extra"],
        "preferred_companies_or_sectors": ["Airports", "Transportation", "Public sector", "Health", "Gov", "Extra"],
        "time_available_hours_per_week": 6,
        "tone_preference": "practical",
        "career_stage": "mid_career_leader",
    }

    req = CareerInsightRequest.model_validate(payload)
    profile = req.user_profile
    assert profile is not None
    assert profile.current_role_title == "Senior Data Scientist"
    assert profile.target_roles == ["GenAI Architect", "ML Lead", "Director", "Extra"][:5]
    assert len(profile.strengths_top3 or []) == 3
    assert len(profile.gaps_top3 or []) == 3
    assert len(profile.preferred_companies_or_sectors or []) == 5


def test_request_without_user_profile_still_valid():
    req = CareerInsightRequest.model_validate(_base_payload())
    assert req.user_profile is None
