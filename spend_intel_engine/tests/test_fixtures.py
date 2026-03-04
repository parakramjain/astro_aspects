from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SampleAspect:
    aspect: str
    strength: float
    dist: float = 0.5
    characteristics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SampleLifeEvent:
    aspect: str
    aspectNature: str
    startDate: str
    endDate: str
    exactDate: str
    eventType: str = "MAJOR"
    description: str = "sample"


@dataclass
class SamplePlanet:
    planetName: str
    planetSign: str
    houseNumber: int
    houseSign: str


@dataclass
class SampleNatalChart:
    planets: List[SamplePlanet]


def sample_natal_chart() -> SampleNatalChart:
    return SampleNatalChart(
        planets=[
            SamplePlanet("Venus", "Libra", 1, "ARIES"),
            SamplePlanet("Saturn", "Capricorn", 10, "CAPRICORN"),
            SamplePlanet("Jupiter", "Sagittarius", 2, "TAURUS"),
            SamplePlanet("Mercury", "Virgo", 4, "CANCER"),
            SamplePlanet("Moon", "Cancer", 8, "SCORPIO"),
            SamplePlanet("Mars", "Aries", 7, "LIBRA"),
            SamplePlanet("Sun", "Leo", 5, "LEO"),
        ]
    )


def sample_natal_aspects() -> List[SampleAspect]:
    return [
        SampleAspect(aspect="SUN TRI JUP", strength=0.85),
        SampleAspect(aspect="MER SQR SAT", strength=0.72),
        SampleAspect(aspect="VEN TRI JUP", strength=0.9),
        SampleAspect(aspect="MOO SEX VEN", strength=0.78),
    ]


def sample_life_events() -> List[SampleLifeEvent]:
    return [
        SampleLifeEvent(
            aspect="Jup Sxt Mar",
            aspectNature="Positive",
            startDate="2026-02-20",
            endDate="2026-02-24",
            exactDate="2026-02-22",
            eventType="MAJOR",
            description="optimistic",
        ),
        SampleLifeEvent(
            aspect="Sat Sqr Ven",
            aspectNature="Negative",
            startDate="2026-02-20",
            endDate="2026-02-24",
            exactDate="2026-02-23",
            eventType="MINOR",
            description="restrictive",
        ),
    ]
