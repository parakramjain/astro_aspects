# Calculate Natal services.
    # A. Natal Planet Positions
    # B. Natal Aspects
    # C. Natal Houses
    # D. Natal Dignities
    # E. Natal Chart Summary
    # from datetime import date, time

import os
from typing import Dict
import pandas as pd
from astro_core.astro_core import (
    _planet_name_short,
    calc_planet_pos,
    find_aspects,
    ASPECTS,
    ASPECT_ORB_DEG,
    TRANSIT_ORB_BY_PID,
    effective_orb,
    get_flags,
)

# Use centralized flags from astro_core
FLAGS = get_flags()

# Orb value for aspect consideration
NATAL_ORBS = {
    0: 5.0,
    1: 5.0,
    2: 5.0,
    3: 5.0,
    4: 5.0,
    5: 5.0,
    6: 2.0,
    7: 1.0,
    8: 1.0,
    9: 1.0,
}
ASPECT_ORB_DEG: Dict[int, float] = {
    0:   8.0,   # Conjunction
    60:  6.0,   # Sextile
    90:  7.0,   # Square
    120: 8.0,   # Trine
    180: 8.0,   # Opposition
}
# Calculate Natal Planet Positions
def calculate_natal_positions(
    birth_date: str,
    birth_time: str,
    birth_tz: str = "UTC",
    flags: int | None = None,
    with_planet_name: bool = True
) -> Dict[int, float]:
    """
    Calculate natal planet positions for given birth details.
    Returns a dictionary mapping planet IDs (int) to their zodiac positions in degrees.
    """
    natal_pos = calc_planet_pos(birth_date, birth_time, tz_str=birth_tz, flags=(flags if flags is not None else get_flags()))
    natal_pos_out = {}
    for pid, pos in natal_pos.items():
        natal_pos_out[_planet_name_short(pid)] = pos
    if with_planet_name:
        return natal_pos_out
    return natal_pos

def calculate_natal_aspects(
    natal_positions: Dict[int, float],
    orb_values: Dict[int, float] = ASPECT_ORB_DEG,
) -> list:
    """
    Calculate natal aspects based on planet positions and orb values.
    Returns a DataFrame with aspect details.
    """
    aspects = find_aspects(natal_positions, natal_positions, aspect_orbs=orb_values)
    aspect_rows = []
    Total_aspects_found = 0
    conjunction_aspects_count = 0
    for aspect in aspects:
        Total_aspects_found += 1
        # print("Aspect found: ", aspect)
        if aspect.aspect_code == 'Con':
            conjunction_aspects_count += 1
            continue
        else:
            aspect_rows.append({
                "Planet A": aspect.natal_planet,
                "Aspect": aspect.aspect_code,
                "Planet B": aspect.transit_planet,
                "Exact Angle": aspect.delta_deg,
            })
    # print("Total Conjunction Aspects found: ", conjunction_aspects_count)
    # print("Total Aspects found: ", Total_aspects_found)
    return aspect_rows
    # return pd.DataFrame(aspect_rows)

if __name__ == "__main__":
    # Example usage
    birth_date = "1951-08-04"
    birth_time = "16:00"
    birth_tz = "Asia/Kolkata"
    
    natal_positions = calculate_natal_positions(birth_date, birth_time, birth_tz)
    # print("natal_positions: ", natal_positions)
    for planet_name, pos in natal_positions.items():
        print(f"{planet_name},  Position {pos:.2f}°")
    
    natal_positions = calculate_natal_positions(birth_date, birth_time, birth_tz, with_planet_name=False)
    natal_aspects = calculate_natal_aspects(natal_positions)
    # print(natal_aspects)

    # Print Natal Aspects in proper format
    print("Natal Aspects:")
    # print(natal_aspects)
    for row in natal_aspects:
        print(f"  {row['Planet A']} {row['Aspect']} {row['Planet B']} ({row['Exact Angle']:.2f}°)")