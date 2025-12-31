from datetime import date

import pytest

from core.datastore.model import TransactionDirection
from core.utils import (
    cents_to_dollars,
    derive_direction,
    derive_month_context,
    dollars_to_cents,
)


class TestDollarsToCents:
    def test_integer_amount(self):
        assert dollars_to_cents(10) == 1000

    def test_float_amount(self):
        assert dollars_to_cents(10.25) == 1025

    def test_string_amount(self):
        assert dollars_to_cents("5.50") == 550

    def test_round_half_up(self):
        assert dollars_to_cents(1.005) == 101
        assert dollars_to_cents(1.004) == 100

    def test_negative_amount(self):
        assert dollars_to_cents(-2.34) == -234


class TestCentsToDollars:
    def test_integer_amount(self):
        assert cents_to_dollars(1000) == 10.0

    def test_float_amount(self):
        assert cents_to_dollars(1025) == 10.25

    def test_string_amount(self):
        assert cents_to_dollars(550) == 5.5

    def test_round_half_up(self):
        assert cents_to_dollars(101) == 1.01
        assert cents_to_dollars(100) == 1.0

    def test_negative_amount(self):
        assert cents_to_dollars(-234) == -2.34


class TestDeriveDirection:
    @pytest.mark.parametrize(
        "amount_cents,is_credit_card,expected",
        [
            (100, True, TransactionDirection.OUT),
            (-100, True, TransactionDirection.IN),
            (0, True, TransactionDirection.IN),
            (-100, False, TransactionDirection.OUT),
            (100, False, TransactionDirection.IN),
            (0, False, TransactionDirection.IN),
        ],
    )
    def test_direction(self, amount_cents, is_credit_card, expected):
        assert derive_direction(amount_cents, is_credit_card) == expected


class TestDeriveMonthContext:
    def test_current_month_defaults(self):
        ctx = derive_month_context()
        today = date.today()

        assert ctx["current_month"] == today.month
        assert ctx["year"] == today.year
        assert ctx["readonly"] is False

    def test_previous_month_rollover(self):
        ctx = derive_month_context(month=0, year=2025)

        assert ctx["current_month"] == 12
        assert ctx["year"] == 2024
        assert ctx["prev_month"] == 11
        assert ctx["next_month"] == 13

    def test_next_month_rollover(self):
        ctx = derive_month_context(month=13, year=2025)

        assert ctx["current_month"] == 1
        assert ctx["year"] == 2026
        assert ctx["prev_month"] == 0
        assert ctx["next_month"] == 2

    def test_readonly_for_non_current_month(self):
        today = date.today()

        ctx = derive_month_context(month=today.month - 1, year=today.year)
        assert ctx["readonly"] is True
        assert ctx["year"] == today.year
        assert ctx["current_month"] == today.month - 1
