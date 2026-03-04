from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date

from spend_intel_engine.domain.models import BirthPayload, ShoppingCfg
from spend_intel_engine.shopping_engine import compute_shopping_insights


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute astrology shopping insights")
    parser.add_argument("--name", required=True)
    parser.add_argument("--dob", required=True, help="YYYY-MM-DD")
    parser.add_argument("--tob", required=True, help="HH:MM[:SS]")
    parser.add_argument("--place", required=True)
    parser.add_argument("--tz", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--start-date", default=date.today().isoformat())
    parser.add_argument("--n-days", default=14, type=int)

    parser.add_argument("--natal-spend-csv")
    parser.add_argument("--transit-csv")
    parser.add_argument("--signals-csv")
    parser.add_argument("--moon-csv")
    return parser


def main() -> None:
    args = _parser().parse_args()
    default_cfg = ShoppingCfg()

    payload = BirthPayload(
        name=args.name,
        dateOfBirth=args.dob,
        timeOfBirth=args.tob,
        placeOfBirth=args.place,
        timeZone=args.tz,
        latitude=args.lat,
        longitude=args.lon,
        lang_code=args.lang,
    )

    cfg = ShoppingCfg(
        natal_spend_aspects_csv=args.natal_spend_csv or default_cfg.natal_spend_aspects_csv,
        transit_daily_shopping_aspects_csv=args.transit_csv or default_cfg.transit_daily_shopping_aspects_csv,
        natal_structure_signals_csv=args.signals_csv or default_cfg.natal_structure_signals_csv,
        moon_spending_aspects_csv=args.moon_csv or default_cfg.moon_spending_aspects_csv,
    )

    insights = compute_shopping_insights(
        payload=payload,
        start_date=date.fromisoformat(args.start_date),
        n_days=args.n_days,
        cfg=cfg,
    )

    print(json.dumps(asdict(insights), indent=2, default=str))


if __name__ == "__main__":
    main()
