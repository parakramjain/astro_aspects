from __future__ import annotations

from typing import Dict

def _clip_0_100(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


class CareerMomentumEngine:
    def __init__(self, config: Dict):
        self.config = config

    def compute(
        self,
        *,
        timing_strength: float,
        execution_stability: float,
        risk_pressure: float,
        growth_leverage: float,
    ) -> int:
        weights = self.config.get("weights", {}).get("momentum", {})
        inverse_risk = 100.0 - risk_pressure
        score = (
            float(weights.get("timing_strength", 0.35)) * timing_strength
            + float(weights.get("execution_stability", 0.30)) * execution_stability
            + float(weights.get("inverse_risk_pressure", 0.20)) * inverse_risk
            + float(weights.get("growth_leverage", 0.15)) * growth_leverage
        )
        return _clip_0_100(score)
