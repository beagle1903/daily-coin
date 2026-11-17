"""Number formatting for the CLI that stays readable for sub-cent coins."""
import math

SMALL_VALUE_SIGNIFICANT_DIGITS = 4


def format_number(value: float) -> str:
    """
    Two decimals for values of magnitude 1 or more (with thousands separators);
    below that, SMALL_VALUE_SIGNIFICANT_DIGITS significant digits, so 0.0000245
    stays 0.00002450 instead of rounding to 0.0000. Never uses exponent notation.
    """
    if value == 0 or not math.isfinite(value):
        return f"{value:.2f}"
    magnitude = abs(value)
    if magnitude >= 1:
        return f"{value:,.2f}"
    decimals = SMALL_VALUE_SIGNIFICANT_DIGITS - 1 - math.floor(math.log10(magnitude))
    return f"{value:.{decimals}f}"


def format_price(price: float) -> str:
    return f"${format_number(price)}"
