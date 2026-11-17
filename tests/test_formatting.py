import pytest

from formatting import format_number, format_price


@pytest.mark.parametrize("value, expected", [
    (95230.15, "95,230.15"),
    (1.78, "1.78"),
    (1.0, "1.00"),
    (-4.0, "-4.00"),
    (0.68, "0.6800"),
    (0.000175, "0.0001750"),
    (0.0000245, "0.00002450"),
    (-0.0042, "-0.004200"),
    (0.0, "0.00"),
])
def test_format_number(value, expected):
    assert format_number(value) == expected


def test_sub_cent_values_never_render_as_zero_or_exponent():
    for value in (0.0000245, 0.0000142, 0.00000099):
        text = format_number(value)
        assert "e" not in text
        assert float(text) != 0


def test_format_price():
    assert format_price(0.0000245) == "$0.00002450"
    assert format_price(95230.15) == "$95,230.15"
