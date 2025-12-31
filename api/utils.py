from decimal import ROUND_HALF_UP, Decimal

from api.datastore.model import TransactionDirection


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
