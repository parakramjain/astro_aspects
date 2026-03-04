from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code, symmetric_keys


def test_aspect_normalization_variants():
    assert normalize_aspect_code("Jup Sxt Mar") == "JUP SEX MAR"
    assert normalize_aspect_code("mer square sat") == "MER SQR SAT"
    assert normalize_aspect_code("Ven Trine Jup") == "VEN TRI JUP"
    assert normalize_aspect_code("Sun Conj Moon") == "SUN CON MOO"


def test_symmetric_keys_match_reverse():
    direct, reverse = symmetric_keys("VEN TRI JUP")
    assert direct == "VEN TRI JUP"
    assert reverse == "JUP TRI VEN"
