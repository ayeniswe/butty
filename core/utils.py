from calendar import month_name
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from core.datastore.model import TransactionDirection


def dollars_to_cents(amount: float | str) -> int:
    return int(
        (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def cents_to_dollars(amount_cents: int) -> float:
    return float((Decimal(amount_cents) / 100).quantize(Decimal("0.01")))


def derive_direction(amount_cents: int, is_credit_card: bool):
    if is_credit_card:
        return TransactionDirection.OUT if amount_cents > 0 else TransactionDirection.IN
    else:
        return TransactionDirection.OUT if amount_cents < 0 else TransactionDirection.IN


def derive_month_context(month: int | None = None, year: int | None = None):
    now = datetime.now()

    base_year = year if year is not None else now.year
    base_month = month if month is not None else now.month

    # Normalize month overflow/underflow (e.g. 0, 13, -1)
    year_offset, normalized_month = divmod(base_month - 1, 12)
    current_year = base_year + year_offset
    current_month = normalized_month + 1

    current = datetime(year=current_year, month=current_month, day=1)

    return {
        "current_month_name": month_name[current.month][0:3],
        "current_month": current.month,
        "prev_year": current.year - 1 if current.month == 1 else current.year,
        "year": current.year,
        "now_year": now.year,
        "now_month": now.month,
        "readonly": (current_year == now.year and current.month < now.month)
        or (current_year < now.year),
        "next_month": current.month + 1,
        "prev_month": current.month - 1,
    }
