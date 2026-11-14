"""Numeric input contract: one decimal separator, no thousands grouping."""
import math
import re

_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:[.,][0-9]+)?|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


def parse_number(value, label, *, optional=False, minimum=None, maximum=None, integer=False):
    """Return a finite float (or None for optional absence); never coerce blanks/bools to zero."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if optional:
            return None
        raise ValueError(f'{label}: a number is required.')
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f'{label}: invalid number.')
    if isinstance(value, str):
        value = value.strip()
        if not _DECIMAL.fullmatch(value):
            raise ValueError(f'{label}: use one decimal separator (point or comma), without grouping.')
        value = value.replace(',', '.')
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(f'{label}: invalid number.') from error
    if not math.isfinite(result):
        raise ValueError(f'{label}: a finite number is required.')
    if integer and not result.is_integer():
        raise ValueError(f'{label}: an integer is required.')
    if (minimum is not None and result < minimum) or (maximum is not None and result > maximum):
        raise ValueError(f'{label}: number outside the allowed range.')
    return result
