from services.indicators import calculate_evi, calculate_nbr, calculate_ndvi, calculate_savi


def test_calculate_ndvi() -> None:
    assert calculate_ndvi(0.72, 0.16) == 0.6364


def test_calculate_savi() -> None:
    assert calculate_savi(0.72, 0.16) == 0.6087


def test_calculate_evi() -> None:
    assert calculate_evi(0.72, 0.16, 0.08) == 0.6731


def test_calculate_nbr() -> None:
    assert calculate_nbr(0.72, 0.22) == 0.5319


def test_zero_denominator_returns_zero() -> None:
    assert calculate_ndvi(0.0, 0.0) == 0.0
    assert calculate_nbr(0.0, 0.0) == 0.0
