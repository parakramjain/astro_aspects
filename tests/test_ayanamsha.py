import datetime as dt
import unittest

# Ensure workspace root is on sys.path if needed
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import swisseph as swe
import astro_core.astro_core as ac

class TestAyanamsha(unittest.TestCase):
    def test_sidereal_vs_tropical(self):
        # Known instant
        dtu = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=dt.UTC)

        # Sidereal Lahiri
        ac.set_ayanamsha("sidereal", "Lahiri", None)
        lon_sid = ac._planet_longitudes_utc(dtu)[swe.SUN]

        # Tropical
        ac.set_ayanamsha("tropical", "Tropical", None)
        lon_tro = ac._planet_longitudes_utc(dtu)[swe.SUN]

        delta = abs((lon_tro - lon_sid) % 360.0)
        if delta > 180:
            delta = 360.0 - delta
        # Should be around ~23-24 degrees for year 2000
        self.assertGreater(delta, 15.0)
        self.assertLess(delta, 30.0)

    def test_user_custom_offset(self):
        dtu = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
        # Tropical baseline
        ac.set_ayanamsha("tropical", "Tropical", None)
        lon_tro = ac._planet_longitudes_utc(dtu)[swe.SUN]

        # USER sidereal with 23.85 deg custom offset should produce a different
        # value than tropical and (likely) different from Lahiri; exact delta
        # can vary with library build conventions.
        ac.set_ayanamsha("sidereal", "USER", 23.85)
        lon_user = ac._planet_longitudes_utc(dtu)[swe.SUN]

        # Different from tropical by a meaningful amount
        delta_tu = abs((lon_tro - lon_user) % 360.0)
        if delta_tu > 180:
            delta_tu = 360.0 - delta_tu
        self.assertGreater(delta_tu, 5.0)

        # Also compare against Lahiri to ensure the setting takes effect
        ac.set_ayanamsha("sidereal", "Lahiri", None)
        lon_lah = ac._planet_longitudes_utc(dtu)[swe.SUN]
        delta_ul = abs((lon_user - lon_lah) % 360.0)
        if delta_ul > 180:
            delta_ul = 360.0 - delta_ul
        self.assertGreaterEqual(delta_ul, 0.1)

if __name__ == "__main__":
    unittest.main()
