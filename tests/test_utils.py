from datetime import date

import pytest

from core.datastore.model import TransactionDirection
from core.utils import (
    build_fingerprint,
    cents_to_dollars,
    derive_direction,
    derive_month_context,
    dollars_to_cents,
    normalize,
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
        ctx = derive_month_context(month=12, year=2025)
        assert ctx["readonly"] is True
        assert ctx["year"] == 2025
        assert ctx["current_month"] == 12


class TestNormalize:
    def test_none_returns_empty(self):
        assert normalize(None) == ""

    def test_empty_string(self):
        assert normalize("") == ""

    def test_trim_and_lowercase(self):
        assert normalize("  Hello World  ") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize("Hello    World   Again") == "hello world again"

    def test_mixed_case_and_tabs(self):
        assert normalize("  HeLLo\tWoRLD ") == "hello world"


class TestBuildFingerprint:
    def test_same_inputs_produce_same_fingerprint(self):
        fp1 = build_fingerprint("Account", "Checking", "1234")
        fp2 = build_fingerprint("Account", "Checking", "1234")
        assert fp1 == fp2

    def test_order_matters(self):
        fp1 = build_fingerprint("a", "b")
        fp2 = build_fingerprint("b", "a")
        assert fp1 != fp2

    def test_multiple_values(self):
        fp1 = build_fingerprint("acc", "2025-01-01", "1000", "walmart")
        fp2 = build_fingerprint("acc", "2025-01-01", "1000", "walmart")
        assert fp1 == fp2
