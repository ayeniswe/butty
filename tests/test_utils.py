import pytest
from datastore.model import TransactionDirection
from utils import derive_direction, dollars_to_cents


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
