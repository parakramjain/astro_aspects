from __future__ import annotations

from enum import Enum
from typing import Dict


class SpendCategory(str, Enum):
    ULTRA_THRIFTY = "Ultra Thrifty"
    THRIFTY = "Thrifty"
    BALANCED = "Balanced"
    SPENDER = "Spender"
    IMPULSIVE = "Impulsive/High-Spend Risk"


class PurchaseType(str, Enum):
    ESSENTIALS = "essentials"
    BIG_TICKET = "big_ticket"
    LUXURY = "luxury"


# Purchase type amplitude configuration
BASE_AMPLITUDE: Dict[str, float] = {
    "essentials": 0.6,
    "big_ticket": 1.0,
    "luxury": 1.25,
}

# Purchase type risk multipliers for hard aspects
RISK_MULTIPLIER: Dict[str, float] = {
    "essentials": 0.7,
    "big_ticket": 1.0,
    "luxury": 1.4,
}
